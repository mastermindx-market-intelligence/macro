# Russell completed-close freshness and cache-custody repair

**Date:** 2026-10-15. **Commission:** original rotation-intelligence/Prophet readiness program. **Operation:** `rotation-russell-close-truth-20261015-sol`. **State:** isolated source, not merged or installed. **Macro source base:** `376a038514bb1dffcc4bd9ff770df3a8e6d5b689`. Reused protected compatible procedure pin: Mastermind `2cc4942e136ad4fb544fd5c72ab1856608a5dac1`, Skillpack 1.0.1 / bootstrap 1.

## Source evidence and the consumer failure

Current public `www.mastermind-x.com/us_stocks.html` (read 2026-10-15) displays a new 2026-10-14 market/candidate board, but the ranked Prophet prices are explicitly dated 2026-10-07, five NYSE sessions behind. Native main `site/factordata/us_standouts.json` blob `7774d968ba4ccc9f5a1b9e3de69f72d2f9f11895` (read via GitHub) has `as_of=2026-10-14`, emitted 2026-10-15T15:42:18Z, 105 buy rows, 186 eligible. Its source `staleness` states `price_through=2026-10-07`, `max_through=2026-10-14`, `panel.majority_through=2026-10-07`, `panel.members_at_through=1176`, `members_total=3063`, `mixed_vintage=true`. This is a *freshly generated mixed-vintage panel*, not a missing generator or new forecast. The existing global delayed guard correctly refuses to declare it current.

Actual 2026-10-15 daily Actions run 38661819472 collected through Oct 14; its runner restored the Russell cached close panel via `russell-closes-38661819472` and ranked source consumers. The collect log reports the original Finviz idx_rut scrape failed HTTP 403; a stale 16.9-day source led to the existing 1,971-constituent fallback. The Russell price collector saw mixed adjustment-basis seams for 235 tickers (with several unsuccessful full-window refetches), and reported `ok` because its 945 time-index rows reached 2026-10-14; that is not proof that every constituent had a current close. The engine's universe report included 1,356 net-new Russell members after preferred deeper/large/mid/small inputs.

Read-only inspection of actual runner caches: S&P close matrices have many October 14 constituents while the Russell cache was no longer present in the completed runner checkout at investigation time. That cleanup means the precise Russell modal-price histogram **cannot** be claimed from that runner; the global source panel's modal October 7 is proven by the published artifact. Historical PR #7206 independently recorded a previous Russell run with only 21 of 1,943 requested current closes. Neither proves exact present Yahoo causation for each lagging ticker.

## Reproduced code defect

The existing `RussellBreadthAdapter._download_closes` wrote *every* downloaded DataFrame straight to `self.cache_path` **before** `BreadthAdapter.fetch` could verify/merge/publish it. This included one-month tail downloads and tiny split-seam re-downloads into the same canonical full-history cache. When Yahoo returned successfully but with incomplete completed-session adjusted Close fields, the base downloader interpreted the response as success; its global `live_cols` guard checked whether columns had *ever* contained prices, not whether they contained a true completed-session price.

The default first-night partial seed is necessary for interrupted 1,900-name backfills. It does **not** authorize premature overwrites once a last-good cache exists.

## Exact bounded repair

Only `collectors/russell_breadth.py` and its original tests change, alongside this evidence record.

1. Snapshot whether the canonical cache existed **before** a Russell download.
2. For every *full Russell universe* download (including cold starts), freeze one incumbent `nyse_calendar.expected_last_session()` **before the provider request**. This makes a slow download crossing 17:00 ET unable to borrow the new completed session. Compare the response to that frozen source clock. Count only finite positive closes on the exact completed session among the requested names. Require at least 80% coverage; future-dated rows, volume-only, NaN, zero and infinity do not count. Small seam subdownloads remain outside the full-universe health gate.
3. On insufficient coverage, raise an explicit `russell_breadth completed-session close coverage...` error **before** base `fetch()` can write the canonical close cache or publish success. Do not waive the required coverage just because the response contains 900 historical rows.
4. Keep the base 250-member chunk size, original Yahoo provider, retries, adjustment-basis seam repair and permitted data-source set unchanged.
5. Preserve cold-start progress: an absent canonical cache may still be seeded by a historical/backfill (not a 1-month refresh), but a first-night partial full-universe seed **still fails the completed-session source gate**; it cannot certify the run as `ok`. Normal incremental refresh and split-seam subdownloads never write to the canonical path independently. The base `fetch()` owns the successful fully merged cache write.
6. This is an input health guard, **not** candidate discovery, ranking, sizing, entry permission, provider fallback, retry-loop or alert publication.

No existing workstream, queue, data store or price-basis owner is duplicated. No live quote collected; historical files and externally supplied rows were not modified.

## Verification and retained counterexamples

- Exact pre-change baseline `tests/test_russell_breadth.py tests/test_breadth_split_seam.py`: **19 passed** with an installed Python 3.12/yfinance environment. A Python 3.14 sparse interpreter first raised `ModuleNotFoundError: yfinance` before tests could execute; this was a dependency environment mismatch, not a source regression. Changed to the already-installed Python 3.12, no pip install.
- Test-first: five new cases reproduced **four expected failures, one passed** on original source (partial/Yahoo-success current close, future/nonfinite values, premature normal update write, premature seam write, first-night seed).
- Repaired isolated source: five focused cases passed.
- Two native `RussellBreadthAdapter.fetch` integration cases (actual inherited owner) confirm stale response refuses before any cache/constituent commit and a healthy response permits normal post-verification cache publication.
- Three further test-first cases include the full-sized first-night partial backfill (RED then GREEN), a healthy cold-start control, and a frozen original session while an underlying provider advances the wall clock mid-call (RED then GREEN). Two additional integer threshold controls pin 1359/1700 refusal and 1360/1700 acceptance, respectively.
- Comprehensive affected suite `tests/test_russell_breadth.py tests/test_breadth_split_seam.py tests/test_universe_split_seam.py tests/test_closes_panel_freshness.py`: **70 passed**, existing external temp-directory and pandas deprecation warnings. Python 3.12 compilation and diff check passed. These are fixture/local source tests, not independently reviewed hosted checks.
- The original Russell test module is already registered in `.github/ci/legacy-jobs.yml` under the existing suite; no CI job and no new scheduler are created.
- Full on-runner provider/market-data, independent source review, hosted CI and production browser tests remain **NOT PROVEN**.

## Collision and next steps

Existing #7200 repairs sibling S&P breadth downloads (owns shared `collectors/breadth.py`), #7206 repairs preferred deep-stock closes (owns `collectors/sector_holdings.py`), and the active Prophet R6/PR #9369 owns `scripts/build_stock_library.py`. Their code and original custody are **untouched**; the Russell subclass is a distinct unoccupied source path. Integrate sibling contracts on actual latest main before protected merge, never assume these old PRs merged.

This correction makes Russell's collector **fail visibly** rather than silently mint a refreshed green result from incomplete prices, and avoids losing its recoverable historical cache. It does not by itself turn a partial vendor response into fresh prices. Next consumer-critical requirement is a verified data-source path capable of meeting the current-session Russell coverage threshold, then a naturally scheduled run that produces a qualified price panel across the **whole** Prophet universe, B4 entry evidence and served result. Do not unblock trades, relabel old prices or infer trading profitability from passing fixture tests.

Mission remains **OPEN**. No automatic publisher, account permission, protected-main merge, live alert, operator trade or hosted job dispatch was performed by this local implementation.
