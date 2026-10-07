---
workstream: "WS:MARKET-OS"
session: sol/web-market-holiday-awareness-20261007-sol-001
model: sol
ended_because: ci_handoff
mission: >
  Implement exchange-aware retained cash-market observations and visible holiday status
  for mainland China, Hong Kong, US and Canada, including China's extended breaks.
  This is a bounded existing-owner maintenance commission from the current Chairman
  instruction, not a start or completion of another Market OS product wave.
state_before: >
  Legacy holiday approximations and weekday-only live status produced incorrect closures
  and freshness expectations. Independent adjusted-window and snapshot writers could
  replace newer valid observations with stale provider responses. A live refresh clock
  could masquerade as a trade clock, and the US-hours overlay was the only session publisher.
changed:
  - path: research/MARKET_HOLIDAY_DATA_CONTRACT_2026-10-07.md
    what: Official holiday assessment, coverage boundaries, data/time invariants, existing owners and release proof contract.
  - path: lib/exchange_holidays.py
    what: Source-backed complete annual closure slates, bilingual names, half sessions and explicit coverage provenance.
  - path: lib/market_session.py
    what: Shared pure cash-session status, expected completed date, freshness, expiry and listing-venue routing.
  - path: lib/market_observations.py
    what: Actual provider-date acceptance and complete adjusted-column retention guards.
  - path: collectors/base.py
    what: Explicit cash-adapter observation filtering and retained-store health without changing noncash cadence.
  - path: lib/store.py
    what: Prevent older or empty adjusted windows from deleting the last good complete series.
  - path: engine/live_overlay.py
    what: Preserve baseline and actual history dates, validate quote clocks, hold closures and reuse regional price owners.
  - path: scripts/build_live_quotes.py
    what: Publish the same calendar receipts on the existing minutely snapshot without additional provider requests.
  - path: templates/live.js
    what: Bilingual closure/next-opening/status strip and common guarded polling/WebSocket updates; site/live.js is its paired asset.
verified:
  - claim: Calendar, collector, storage, provider, live projection and import-name regressions passed as one integrated matrix.
    command: >
      MM_DATA_GUARD=1 PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -m pytest -q
      -p no:cacheprovider --basetemp=/Volumes/Mastermind/test-tmp/market-holiday-awareness-20261007-sol-001/integration-final
      tests/test_exchange_holiday_notices.py tests/test_market_session.py tests/test_cn_calendar.py
      tests/test_nyse_calendar.py tests/test_tsx_calendar.py tests/test_hk_freshness.py
      tests/test_market_holiday_collector_freshness.py tests/test_store_holiday_retention.py
      tests/test_store_guard.py tests/test_upsert_basis_guard.py tests/test_live_holiday_overlay.py
      tests/test_live_overlay.py tests/test_live_quotes_settle_window.py tests/test_build_live_quotes.py
      tests/test_hk_southbound_holiday_retention.py tests/test_tushare_holiday_retention.py
      tests/test_universe_holiday_retention.py tests/test_adjust_seam.py tests/test_universe_split_seam.py
      tests/test_tushare.py tests/test_tushare_chips_distribution.py tests/test_cn_intel_pit_accrual.py
      tests/test_tushare_freshness.py tests/test_hk_stock_signals.py tests/test_first_party_import_names.py --tb=short
    result: >
      583 passed, 33 incumbent Timestamp.utcnow deprecation warnings, 124.36 seconds,
      PID97334 exit0. This matrix preceded the final US StockPriceAdapter opt-in and
      snapshot-session client integration; the final scoped receipts below close those follow-ups.
  - claim: Direct-writer independent review resolved both demonstrated retention blockers.
    command: >
      Independent read-only review of exact source/test diffs and hashes for the four calendars,
      market_observations, store, CN/CA/HK universe, Tushare and southbound writers.
    result: >
      PASS after fixing raised full-repull exceptions and unverified historical holiday deletion.
      Author final direct-retention/seam gate76 passed in7.21s. Actual HK2021-12-28 survives a full rebase.
  - claim: Around-the-clock calendar publication adds no provider request.
    command: >
      MM_DATA_GUARD=1 /opt/homebrew/bin/python3.12 -m pytest
      tests/test_build_live_quotes.py tests/test_live_holiday_overlay.py -q
    result: >
      Independent95 passed in6.22s, PID8303 exit0. scripts/build_live_quotes.py SHA256
      456510b84af72ecb89d7c155f1966bdbac4c5bb731861accb90482866e0e3452.
  - claim: Final US deep-stock adapter routing preserves holiday and open-session behavior.
    command: >
      MM_DATA_GUARD=1 /opt/homebrew/bin/python3.12 -m pytest
      tests/test_market_holiday_collector_freshness.py tests/test_stock_price_retention.py
      tests/test_hk_freshness.py -q
    result: >
      99 passed in 4.63s, PID19473 exit0. July 3 first reproduced an incorrect holiday write;
      the fixed actual adapter retains July 2 with zero writes while the July 6 control advances.
  - claim: Incumbent overlay builder schema tests match the extended session contract.
    command: >
      MM_DATA_GUARD=1 PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
      --basetemp=/Volumes/Mastermind/test-tmp/market-holiday-awareness-20261007-sol-001/overlay-schema-green
      tests/test_build_live_overlay.py --tb=short
    result: >
      7 passed in 2.26s, PID11770 exit0. Two obsolete assertions first failed on the added
      Connect key and expanded US receipt. The schema input is now independent of sparse
      production data. Source and final assertions passed independent read-only review.
  - claim: The final CI manifest is packable and new regressions have named code-gate owners.
    command: >
      run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --gate code --pack-count 12
      --validate-only; eight real manifest, ownership, trigger-closure and workflow-size guards;
      infer_job_scopes/select_jobs over sixteen changed test/source paths.
    result: >
      172 jobs validated and eight guards passed in 40.25s, PID61175 exit0.
      Sixteen path probes select the existing NYSE/calendar or HK robustness owner,
      PID61598 exit0. The direct Node command makes the .mjs test a named dependency;
      the incumbent builder schema test now also runs in the HK code gate.
  - claim: Quote clock integrity remains explicit when a bad-print reason has display priority.
    command: >
      MM_DATA_GUARD=1 PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -m pytest -q
      -p no:cacheprovider --basetemp=/Volumes/Mastermind/test-tmp/market-holiday-awareness-20261007-sol-001/quote-clock-fact-green
      tests/test_live_holiday_overlay.py tests/test_live_overlay.py tests/test_build_live_quotes.py --tb=short
    result: >
      121 passed in 4.09s, PID76145 exit0. Five combined bad-print/clock cases first failed;
      quote_clock_invalid now preserves the independent real/synthetic/missing/malformed/future
      clock fact. Existing price retention, rejection and display reasons are unchanged.
  - claim: Final client receipts and quote/history continuity passed behavior and actual-page checks.
    command: >
      node --test tests/live_holiday.test.mjs and its pytest launcher; final-source Chromium
      snapshot/worker/401-overlay fixture matrix plus three independent immutable-client probes.
    result: >
      33 JavaScript behaviors and launcher passed, PID75111 exit0. Eight final-source browser
      cases passed, PID78875 exit0, at 390px ZH dark and 1440px EN light with zero errors or
      added overflow and one snapshot request each. Cases cover healthy/late CN holiday data,
      HK recovery past old combined bad-print/invalid-clock metadata, and a no-quote Canada page.
      Independent review passed receipt ordering, history aging and invalid-clock recovery.
      Final JS pair SHA256 is 2464239d98feaff4d073210275694cc4c0cbcd654a836188bd85d2d1c635db17.
      Browser report is in the operation test directory under ui-visual/fast-snapshot-report.json.
  - claim: Initial client integration was checked against actual page DOM and CSS.
    command: >
      Chromium fixture matrix over four stock boards at390/1440 widths, EN/ZH, light/dark,
      healthy/late states; four macro routes, HK-open/Connect-closed and unknown CN future coverage.
    result: >
      76 cases passed, zero client errors, zero strip overflow and zero added page overflow.
      Reports under /Volumes/Mastermind/test-tmp/market-holiday-awareness-20261007-sol-001/ui-visual/.
      Controlled fixtures remove unrelated scripts in memory; this is not full-site or production proof.
unverified:
  - claim: The committed candidate has completed required hosted checks and deployed production proof.
    what_would_verify: Exact PR head, current-base integration and concluded required checks; governed merge; live served bytes and fresh session receipts; actual regional-page consumer check.
unresolved:
  - Annual CN2027 and complete CA2027 notices are not yet incorporated; coverage remains unverified.
next_actions:
  - Freeze the final source, validate Agent OS and CI ownership, commit and publish the exact candidate.
  - Complete required hosted checks and independent release review on that immutable head and current protected base.
  - Merge through GitHub without bypass, follow the incumbent deployment/publication owners, and verify actual live receipts and regional pages.
  - Record merge, deployment and consumer-proof receipts before declaring the requested outcome complete.
do_not_redo:
  - Do not create another calendar service, scheduler, collector, risk-sizing rule, state store or publication lane.
  - Do not turn Chinese government make-up weekends into stock-market sessions.
  - Do not freeze news, filings, macro releases, FX, futures, crypto or offshore listings by issuer country.
  - Do not use approximate historical holiday arithmetic to delete provider-dated weekdays.
  - Do not suppress preholiday missing sessions or invent a new observation date from a retrieval timestamp.
  - Do not splice different adjustment bases or overwrite complete history after a failed full repull.
  - Do not rely on the US-hours overlay as the sole Asian market-status publisher.
  - Do not run the full repository suite in this sparse carrier or stage unexpected runtime data.
danger_areas:
  - data and most runtime artifacts are omitted in the sparse checkout; legacy test paths must stay isolated.
  - templates/live.js and site/live.js must remain byte-identical; immutable browser cache references require the normal render restamp.
  - Existing open PR8458 also touches quote serialization for private provenance; preserve its independent contract if it lands before this candidate.
  - Unverified calendar coverage is an explicit product state, not a synthetic closure exemption.
---

# Holiday maintenance implementation checkpoint

Capability state at this checkpoint: **BUILT_NOT_PROVEN**. The parent session remains
responsible for the complete delivery chain. The schema's `ci_handoff` marks the transition
to hosted verification and does not end the Chairman's mission or transfer source custody.

## Authority and source identity

- Current direct Chairman instruction: assess and implement correct holiday freezing and
  market-vacation awareness for China, US, HK and Canada.
- Sole operation: `market-holiday-awareness-20261007-sol-001`.
- Registered carrier: `/Volumes/Mastermind/agent-workspaces/macro/web/market-holiday-awareness-20261007-sol-001`.
- Branch: `sol/web-market-holiday-awareness-20261007-sol-001`.
- Acquired Macro base: `e20149308a7bce3327e67f8fe3c387f8bfaf5cbf`.
- Protected Mastermind procedure refreshed to `1fc040f7343dde73fec3556dd3bf9bc8c1b18129`;
  Skillpack1.0.1/schema v1/minimum bootstrap1. INDEX and required procedures were
  reloaded atomically. Movement from `ee120e80f5d5e0344c453dd7cbf4108b9c429b38`
  changes Executive commission consumers and tests, not this maintenance's governing law.
- Macro compatibility comparison through `f0ef0fc0451cd86afeef200b04bcea65f2c2f583`
  found no feature-owned source movement. Shared CI manifest changes touch other jobs;
  rendered/data movement does not substitute for integration proof.

This knowledge record is affiliated with Market OS for recovery. It changes no Market OS
wave, owner, readiness, portfolio population, security-state namespace or strategic registry.
The PR uses the typed maintenance exception rather than inventing a Linear issue or new wave.

## Review and collision receipts

The current open-PR census inspected200 entries. Relevant shared-file carriers are #8458
(private quote provenance), #8270 (visibility pause/resume), #8196 (additional Connect
aggregate collector), #8398 (fund-portfolio tests) and #8144 (Tencent fetch batching).
Their independent functionality was not imported or displaced. #8458 has nearby quote
serialization edits and must be preserved during any future integration. Shared manifest
edits use existing job owners; #8444's manifest patch is in a different product test job.

Independent reviewers did not approve their own implementation tranches. Root reviewed the
collector/freshness and UI changes; separate reviewers checked root's projection/publication
code and the calendar/store/direct writers. The full retained-data contract and official
source links are in `research/MARKET_HOLIDAY_DATA_CONTRACT_2026-10-07.md`.

## Test-isolation incident

Two existing Tushare validation tests wrote a synthetic one-line trial ledger into the omitted
sparse data path because their fixture redirected config.data_dir but not TrialLedger.DEFAULT_PATH.
MM_DATA_GUARD detected both writes. Exact synthetic diagnostics were preserved in the operation's
test temporary directory; only those test-created files were removed and their omitted-path
flag restored. Both fixtures now redirect the ledger into tmp_path. The rerun passed with
data clean. No production data or pre-existing user file was removed.

## Live baseline before release

A read-only probe found the production quote snapshot has no sessions field before this change;
the anonymous overlay route requires authentication. That makes the existing public minutely
snapshot a necessary status carrier. Deployment and current live receipt proof remain pending;
the pre-release browser matrix is controlled evidence only.

Native child agents have no separate Git refs, publication rights or external watchers.
The parent remains the only commit, push, PR, merge and release owner.


## Hosted contract coverage repair

PR #8606 first candidate `bfacfe3556b6c24a8ee23120880b62b0b95e3934` reached the
hosted contract gate against tested base `f245417e99dffd499e344e2ea17ec01ddd285400`.
Run 37588606779 / job 112684463395 identified 75 introduced transitive import-closure
path declarations missing across 21 existing exclusive CI jobs. No payload-schema
or packing-budget violation was reported. The repair adds exactly those 75 leaf
paths to `.github/ci/legacy-jobs.yml`; no prior path, command, gate, threshold or
other parsed job field changes. Independent exact-delta review passed at manifest
SHA256 `a9ad85294b08dec83f2045ab9a16e3dcce5829864c566a53a5ffa21f06846c5b`.

Local shared closure and ordinary-code packing-ceiling checks both passed:
2 tests in 198.17 seconds, PID 44482, exit 0, MM_DATA_GUARD enabled. Manifest validation
passed 172 code jobs, PID 45734, exit 0. This is bounded repair evidence; the full
hosted differential gate on the repaired immutable candidate remains required.
Feature source and accepted backend/client review bindings are unchanged.
Deployment and actual public-page proof remain parent-owned and pending.
