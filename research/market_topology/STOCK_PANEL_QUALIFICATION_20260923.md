# Market topology: stock-panel qualification and a survival-label falsifier

Status: RESEARCH ONLY. The stock-level predictive experiment has NOT run. FABLE_HANDOFF_READY: false.

Operation: `market-topology-research-20260923-astra-001`. Continues Macro draft PR #7812, not a new program or runtime job. Procedure pin remains Mastermind protected master `4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`; source-contract reference is Macro `88a3f1cfd18f391d2802e9086dc00f6fe5545607`. Local data were inspected at checkout HEAD `0f62daf545719e641036be9e5b88101c3af7ab5f`. These identities are intentionally separate.

## 1. Admission decision

The inspected local `data/massive_stock_day` panel FAILS admission for an unqualified stock-level leadership/bottoming forecast test. It remains useful as raw observational input and for these data-quality experiments. This is NOT evidence that the vendor data are defective, that every Mastermind consumer is wrong, or that the canonical R2 copy has the same freshness or consumer-side processing.

The critical reasons are economic comparability and identity, not merely missing rows:

- Flat-file prices are unadjusted. Splits become giant apparent losses when successive raw closes are treated as returns.
- One ticker file can contain different securities across time; conversely, one security can span different ticker files.
- Price availability is not evidence of complete terminal shareholder returns.
- This local checkout lacks the reference/alias and fundamental artifacts needed for the fully matched experiment.
- Its latest sampled market session remains July 2, 2026, not September 2026.

No raw file was changed. No corporate-action healing, identity rebuilding, data refresh, trade, deployment, or new production component was performed.

## 2. Actual census

An executed read-only census used the existing S&P 500 membership-interval artifact, matching ticker spellings literally. Monthly anchors are each calendar month's last observed SPY session, including the partial July 2026 endpoint. This is a nominal coverage audit, not a verified security-identity join.

| Measurement | Result |
|---|---:|
| Top-level local parquet files | 20,476 |
| Membership intervals | 1,255 |
| Distinct historical membership tickers | 1,202 |
| Those tickers with a local file | 856 |
| SPY sessions | 1,254 |
| Observed date span | 2021-07-06 through 2026-07-02 |
| Monthly/latest-partial-month anchors | 61 |
| Sum of nominal member counts at anchors | 30,706 |
| Member-anchor observations with a close | 30,578 |
| Observations with 253 complete trailing closes | 24,242 |
| Missing closes per anchor | 2 to 3 |
| Parquet read errors in inspected files | 0 |

Thus roughly 99.58% of nominal member-anchor observations have a close, despite the material defects below. A near-complete coverage percentage does not qualify the panel economically.

`BF-B` and `BRK-B` are absent under those literal filenames. `SATS` is also absent at the latest inspected anchor. These are unresolved lookup/alias observations, not proof that the underlying securities have no data anywhere. The count of 856/1,202 spans historical tickers from before the local store's start; it must not be misrepresented as contemporary market coverage.

End dates were interpreted inclusively for this audit; the alternative half-open convention changes a total of two member-anchor memberships. Resolve event-effective conventions before research use. The membership producer (`scripts/residual_alpha_pit.py`) identifies a reconstructed, Wikipedia-derived upstream history and best-effort delisted-price recovery. Its current-vintage artifact has no information-availability timestamp. Historical membership is not the same as a contemporaneously archived membership vintage.

Across the full inspected histories of membership-ticker files, 111 files contain 243 adjacent-SPY-session absolute price changes over 40%. These are diagnostics, NOT 243 verified errors and NOT necessarily events occurring while the names were index members. Genuine crashes must not be mechanically repaired as splits or trimmed away.

## 3. Split fixtures: apparent leadership can reverse sign

For each known event, the experiment compares raw prices with a mechanical adjustment of pre-event prices by the announced split ratio. These are selected event fixtures, not a comprehensively repaired panel and not total-return series.

| Ticker; first split-basis trading date | Raw event return | Split-only event return | Raw trailing 63-session return | Split-only trailing 63-session return |
|---|---:|---:|---:|---:|
| NVDA; 2024-06-10; 10:1 | -89.9254% | +0.7461% | -85.8011% | +41.9894% |
| AMZN; 2022-06-06; 20:1 | -94.9003% | +1.9943% | -95.4606% | -9.2126% |
| GOOGL; 2022-07-18; 20:1 | -95.1229% | -2.4580% | -95.6983% | -13.9667% |
| TSLA; 2022-08-25; 3:1 | -66.7819% | -0.3456% | -55.0592% | +34.8224% |

NVDA and TSLA are also below their 50-session simple moving average on the raw basis but above it on the split-only basis at these anchors. This directly demonstrates that data basis can manufacture a loser classification out of an advancing security. It does NOT validate any particular leader classifier.

Primary-source checks: [Massive flat-file contract](https://massive.com/docs/flat-files/stocks/overview) explicitly says stock flat files are unadjusted for splits, dividends and other corporate actions. [Massive adjustment FAQ](https://massive.com/knowledge-base/article/is-massives-stock-data-adjusted-for-splits-or-dividends) distinguishes split-adjusted aggregates from dividend-adjusted returns. [NVIDIA announcement](https://investor.nvidia.com/news/press-release-details/2024/NVIDIA-Announces-Financial-Results-for-First-Quarter-Fiscal-2025/) specifies the 10:1 split and June 10 trading basis. [Amazon's 8-K](https://www.sec.gov/Archives/edgar/data/1018724/000110465922065872/tm2215904d1_8k.htm) specifies the June 6 trading basis. [Alphabet's filing](https://www.sec.gov/Archives/edgar/data/1652044/000165204422000029/goog-20220331.htm) specifies the 20:1 distribution after July 15; the local tape's next-session basis change is July 18. [Tesla announcement](https://ir.tesla.com/press-release/tesla-announces-three-one-stock-split) specifies August 25.

Corrective implication: use the existing corporate-action/data owner and demand an adjustment-basis receipt. Never infer adjustment correctness from a filename or a free-text `adjusted` stamp. Preserve raw tradable prices for historical price eligibility, economic return series for performance, and historical shares for capitalization. Do not multiply back-adjusted prices by today's shares to invent historical size.

## 4. Identity fixtures: META and FB are not timeless securities

The local META file contains a row at January 28, 2022 with close 12.31, then resumes June 9, 2022 at 184.00, a 132-calendar-day gap. A rowwise percentage-change computation bridges it as +1,394.7197%.

This is not Meta Platforms becoming fifteen times more valuable. [Roundhill](https://www.roundhillinvestments.com/etf/metv/) identifies its fund's META-to-METV ticker change effective January 31, 2022. [Meta Platforms](https://investor.atmeta.com/investor-news/press-release-details/2022/Meta-Platforms-Inc.-to-Change-Ticker-Symbol-to-META-on-June-9/default.aspx) identifies its FB-to-META change effective June 9, 2022, with unchanged CUSIP. The tape joins an ETF-era symbol segment to a later common-stock segment.

The local FB file likewise ends its old segment June 8, 2022 at 196.64 and resumes June 26, 2025 at 39.91, after 1,114 calendar days. A rowwise bridge reports -79.7040%. The [ProShares FB fund page](https://www.proshares.com/our-etfs/strategic/fb) identifies FB as its S&P 500 Dynamic Buffer ETF with June 24, 2025 inception. The later FB segment must not be appended to Meta Platforms' shareholder history.

The membership artifact does carry separate FB and META intervals at the 2022 changeover, which is helpful. It does not by itself supply a stable identity join across the price histories. Reindexing to the session calendar with `fill_method=None` prevents the artificial gap-bridging one-day return; that is necessary, but not sufficient to join the right historical segments and preserve uninterrupted economic history through a rename.

The repository already has `scripts/build_security_master.py` and `lib/dataos/identity.py` contracts for security IDs and time-scoped vendor aliases. Their local output directory `data/reference` was absent. Source presence is not a live-output receipt. Do not build a second identity authority or indiscriminately uppercase symbols.

## 5. Terminal outcomes and observation timing

The inspected files end SIVB on March 9, 2023 at 106.04; FRC on April 28, 2023 at 3.51; and ATVI on October 12, 2023 at 94.42. The files contain OHLCV and transaction counts, not complete event settlement, merger consideration, OTC continuation or shareholder-cancellation records.

These last prices are NOT asserted to be final shareholder values. Acquisition, distress, exchange removal, trading halt, bankruptcy filing and cancellation are distinct events. Dropping a name because no forward row exists can bias the exact loser/bottoming question being studied. Imputing every bankruptcy immediately to -100% is also not an observed economic outcome. The [SEC investor bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-84) notes that bankrupt-company shares may continue trading and that reorganization frequently cancels old equity; event-specific evidence is still required. CRSP separately flags [missing delisting values](https://www.crsp.org/wp-content/uploads/appendix/FlagType_RM.html) and [whether terminal returns entered aggregate returns](https://www.crsp.org/wp-content/uploads/appendix/FlagType_DE.html).

[Massive's flat-file quickstart](https://massive.com/docs/flat-files/quickstart) states that a trading day's files are available at approximately 11 a.m. ET the following day. This current documented convention is not an archived release-time record for every historical day. It does mean a flat-file-only replay cannot simply assume yesterday's complete file was known before today's 9:30 a.m. open. Keep observation time, availability time and first executable decision time separate. A faster REST/other feed requires its own proof, not a silently borrowed timestamp.

## 6. Independent experiment: apparent leader survival without predictive information

A synthetic falsifier was executed while stock prediction remained held. It is not market data and not evidence of an investable strategy.

Frozen simulation: seed 2026092302; 300 independent episodes; 500 securities; 83 IID standard-normal log-return increments per security; 63-session formation window; 20-session forward horizon; top quintile defined by cumulative returns. All securities and times are independent, so past information has no population-level predictive content for future increments.

At formation, leaders are the top 100 securities on days 1-63. Compare their membership with (a) the top 100 on days 21-83, and (b) the top 100 on genuinely future days 64-83.

| Measurement | Mean |
|---|---:|
| Retention in overlapping trailing-window leaders | 54.7233% |
| Overlap with future-only leaders | 19.7267% |
| Chance top-quintile overlap | 20.0000% |
| Rank IC, formation versus overlapping trailing window | 0.662728 |
| Rank IC, formation versus genuinely future returns | -0.005422 |

Nominal Monte Carlo 95% interval for mean overlapping-window retention: [54.2850%, 55.1617%]; future-only membership overlap: [19.3307%, 20.1227%]. The one seeded future-rank sample is slightly negative despite a zero population expectation; do not tune seeds or claim a real negative-return effect from it.

The analytic Pearson correlation between the two 63-return sums is 43/63 = 0.682540 because they share 43 IID increments. This overlap mechanically preserves much of the ranking.

Consequence: retrospective state survival is a valid descriptive measurement, but a high survival rate is not by itself evidence of predictive leadership selection. A future leader-survival model must beat mechanical-overlap/null baselines and report genuinely future-only outcomes separately. For horizons longer than the formation window, this particular mechanical overlap disappears; other dependencies can remain.

## 7. Research implications now fixed

1. Keep the earlier negative industry pilot unchanged; this new evidence does not rescue it.
2. Do not run the matched stock forecast on this raw local panel and call the result validated.
3. Do not equate high ticker coverage with security identity, economic comparability or terminal-outcome completeness.
4. Do not interpret top-quintile membership persistence as forward alpha without overlap controls.
5. Do not infer broad market health from a forced fixed-percentile leader count; ranking leaders and measuring an absolute participation population are distinct.
6. Separate return prediction, holding-path risk, descriptive state persistence and prospective recovery confirmation.
7. Continue input qualification through existing Data OS/reference and corporate-action owners. Neural modelling and Fable build commissioning remain held.

The research design for the next comparison is recorded separately in `ORDER_TRANSITION_TRIAL_V1.md`. It is a pre-result protocol with unsatisfied data gates, not an executed experiment or production specification.

## 8. Reproducibility and effects

All artifacts below are on the existing authorized Studio at `/Volumes/Mastermind/research/market-topology-research-20260923-astra-001/`. Raw licensed data were not published.

| Artifact | SHA-256 |
|---|---|
| stock_panel_qualification_v1r1.py | d5f02e0ebfd58c33b0e05e996429b60c9f850c71366c2b8b2902334b7940df73 |
| stock_panel_qualification_v1r1_results.json | f2d4ce91d64414bc09ed2390aff3ba0c0d037ebb73bdb3fd5aa19a44e939a6c9 |
| membership parquet input | 753b414db7fa269d3371d1212d34eba44d99faff44fdb4d454830aed472e6f09 |
| sorted inspected-price-file hash-map encoding | 8d14761bf0ccd1483aa1e247ea88a37005bb729929184afb70c0a47e23c4643d |
| overlap_survival_null_v1.py | ddbffc3235bf5f015908ab89603403bd611c2178f97bfae90f27f7dcbff3f89a |
| overlap_survival_null_v1_results.json | 1fbcb8433de2f7d26e8ee06f0cf68b864a49a90df8109569d191edd824097334 |

Detailed monthly coverage, per-file checks and individual input hashes are in the `stock_panel_qualification_v1r1_*` JSONs. The overlap protocol and per-episode observations are in `overlap_survival_null_v1_protocol.json` and `overlap_survival_null_v1_episodes.json`.

Qualification v1 initially failed while serializing a missing membership end date as non-finite JSON. Its incomplete output and original script were retained; v1r1 fixes serialization and validates JSON before opening each output. Both successful experiments completed with exit code 0. This was an explicit same-host research-script repair, not an ambiguous retry or source-data mutation.

A separate canonical R2 read attempt first failed before network access because the generic Python lacked boto3. The existing project interpreter was discovered with the dependency. The corrected-interpreter read was then blocked by the platform safety check. No successful canonical read or refresh is claimed; the blocked request was not retried through another carrier or mode. Local historical auditing and synthetic research were independently permitted and continued. This does not prove credentials are invalid or R2 is unavailable.
