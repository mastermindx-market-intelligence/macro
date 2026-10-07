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

## Concluded hosted findings and revised integration

The repaired candidate `f29b31c72ca310e5d2c8e87c1994a7f8684008f7` completed hosted
run 37591265599 against tested merge `185674f41cf2e75ac1107514cf74f828eb6c6166`
and base `abb1e6c3da7550eb4d5beca574dbc280bcc96e81`. The full contract-delta
gate passed with zero introduced and zero inherited findings. The complete run
still correctly refused release: pack 10 found the API's missing
`lib/exchange_holidays.py` restart dependency, and pack 3 found an incumbent HK
stale-data fixture dated on a holiday plus missing same-diff P0B browser remints.
These findings were repaired rather than waived.

The API fix was reproduced by the existing import-closure test (PID 81345, exit 1),
then the exact calendar leaf and two explanatory comment lines were added to the
existing restart allowlist. All 253 deployment tests passed (PID 82359).
A genuine concurrent source collision then required integrating pinned main
`e3e3eff48cf4c0b44815d0b066a37fdb65689da0`. Its QBUS news API dependencies,
ticker-news state provisioning, and operator-controlled writer reconciliation
were preserved. The resolved script equals that main plus only the reviewed
calendar repair; all 263 deployment/news-service boundary tests passed
(PID 98964, exit 0).

The new main's ticker-news CI owner required four additional transitive paths:
`lib/exchange_holidays.py`, `lib/market_observations.py`,
`lib/market_session.py`, and `lib/tsx_calendar.py`. The existing absolute
coverage gate first demonstrated those four omissions (PID 98842, exit 1), then
passed after the four additions (PID 20518, 138.96 seconds, exit 0). All other
parsed job fields and previous path order remain intact. Integration preserved
all 246 parsed job definitions, including the concurrent conviction-profile
path union. The ordinary-code packing ceiling passed (PID 7270, 121.52 seconds);
the subsequent four exact leaf additions match none of its three probe paths.
The final manifest validates 174 code jobs (PID 46544, exit 0).

The HK stale-data test retains its July 8 clock, fresh primary stores, and
stale/dead plus degraded/stale assertions. Its observation is now the genuine
June 30 Connect session, five missed sessions earlier, rather than the closed
July 1 date. The original failure was reproduced (PID 25970, exit 1); all 50
HK robustness/freshness tests passed with the existing Python 3.14 runtime
(PID 34565, 3.38 seconds, exit 0). An earlier local Python 3.12 group run lacked
Plotly; all 13 import errors were environment availability, not product failures.
No dependency installation or assertion weakening was used.

Independent read-only review accepted all three exact repair files:

- app/deploy/update.sh: SHA256 `eba2aa35a7a5595f986631f45fccd71d79952076af8e05aa3cd018a2588344c3`
- .github/ci/legacy-jobs.yml: SHA256 `e99c47aa0e77bf727bcc5e49ce569c57abc377377b9541ebf05f350472fc0ae4`
- tests/test_hk_robustness_w5.py: SHA256 `2bdd9ff20354d65bc51b8718e2df18868f1235543bd7e026cea01bb2e4383f8e`

Every previously reviewed feature blob remains identical to the earlier candidate,
apart from the explicitly reviewed CI manifest integration. Browser evidence
reminting does not change the feature implementation.

## Actual current-break data census

A read-only production census at 2026-10-07T08:14:40.127648Z inspected the complete
named CN cash stores: 1,875 stock histories, 28 cash index/ETF histories, and the
1,823 cash columns of china_search/closes.parquet. Footer maxima were all before
October 1, so no bulk price-column read was needed. There were zero October 1–7
rows or non-null cash cells within that coverage. Of the stock histories, 1,866
ended on September 30 and nine already ended earlier; all 28 cash index histories
and the wide panel's shared date index ended on September 30. The panel's shared
index does not prove every constituent column is current. Two noncash files were
excluded. This census makes no provider request, changes no runtime data, and
does not mistake older source observations for current holiday data.

The census is pre-release evidence. The revised immutable candidate still needs
concluded hosted CI, the existing governed squash/release path, actual fresh
session publication and public-page consumption before PROVEN_OUTCOME may be
recorded. The final PR receipt must explicitly supersede the pending-release
clauses of this historical checkpoint once those proofs exist.

## Browser navigation regression exposed by the session strip

The required HK P0B remint exposed a real pending-composer navigation regression.
A controlled comparison used the identical canonical route handler, HTML, assets,
initialization, layout/screenshot setup and mobileBehavior function. The current
live.js failed the pending EN/dark Buy-to-Near sequence while the prior exact
live.js passed. The status strip changed geometry: a native fragment jump moved
the stationary mouse over the unrelated Blocked-stage tooltip. Pointerover at
850.8 ms scheduled its opening; hashchange at 853.4 ms preceded the actual open
at 952.6 ms. The resulting sheet and scrim intercepted the next link. The settled
composer-failed/light controls passed. A touch-capable context still using the
canonical mouse clicks reproduced the pending failure; this is not native-touch
proof. The diagnostic receipt SHA256 is
`75cf8275e7c73f02cbbffd6ae889c394915e590eb9302cc81610be38331e39e9`.

The repair adds only a comment and `window.addEventListener('hashchange', hide)`
beside the existing resize listener in both theme copies. The existing hide
function cancels pending timers even before the popup exists and closes an open
popup through its established cleanup. The template and emitted asset retain
their respective configuration and Terminal bundle bytes. Independent review
accepted template SHA256
`df579ac567bba69f57b77db61b321999a6e1fbe07e9843631f199bb581cb9daf`
and emitted SHA256
`a16c1bd5b07384786362947d47a842f2cfe7861f3d36156606e372864bedc44a`.

An identical deterministic harness executing each actual lens IIFE first showed
four navigation failures and 14 passing controls (PID 53781, exit 1), then passed
all 18 cases after the repair (PID 56624, exit 0). Separate sheet-state controls
confirm removal of popup, scrim, scroll lock, trigger accent and aria-describedby.
Ordinary hover, focus, touch toggle, nested-control behavior and Escape remain
passing. The existing lens suite passed 21 tests with one incumbent skip because
the current hub bake has no dot-symbol ticker; both Node syntax checks passed.
The canonical fixture renderer and browser verifier remain unchanged. Both full
HK and Canada receipts are being reminted against the final theme asset before
this candidate can be submitted for concluded hosted verification.

## Final browser receipts and source compatibility

Both full canonical browser runs completed on the unchanged verifier and final
source bytes. HK passed in 249.713 seconds (parent PID 61999 / Node 62013, exit 0);
Canada passed in 244.376 seconds (parent PID 72751 / Node 72763, exit 0). Both used
Chromium 151.0.7922.34 and produced no stderr. Each receipt passes all seven page
states, eight expansion cases, six fragment cases, eleven desktop sequence cases,
48 primary owner cases, 16 degraded controls and eight persisted screenshots.
Canada also passes all seven quote-state cases. Root read both complete result
structures and found no false pass field. HK's pending EN/dark fallback sequence
now passes using normal click actionability and the original timeouts.

- `mockups/evidence/prophet-p0b-zero-fouc/mobile-layout.json`: SHA256 `a0e16a90fab180861306ed2344ca3179583e159e602d8a3d5f3a6c192ae9fd23`
- `mockups/evidence/prophet-p0b-zero-fouc/mobile-layout-canada.json`: SHA256 `95329f4fc82779669788bd4443a5caa62f816014122ce349148c1e4950e99132`

Both pin live.js `2464239d98feaff4d073210275694cc4c0cbcd654a836188bd85d2d1c635db17`
and emitted theme.js `a16c1bd5b07384786362947d47a842f2cfe7861f3d36156606e372864bedc44a`.
The fixture recipe remains deterministic and its receipt retains SHA256
`747b63f0dfb9b98757cefb49d5d0efd7e9d6c43de2bf2222c279a54b94d69762`.
The historical baseline objects are identical to the existing main objects and
still recover through their original exact head/tree. These are reproducible
browser-fixture proofs with an explicit production claim of none.

The latest source compatibility check at 2026-10-07T09:25:42Z compared integrated
main e3e3eff48cf4c0b44815d0b066a37fdb65689da0 with
1ba1b06cc516113896d71d8143b8c0def3e1a8ae. No holiday-owned source or browser receipt
pin moved. The only owned-path intersection is the shared CI manifest; its newer
edit adds two tests to the separate, nonexclusive research-vault job. No affected
job overlaps the holiday manifest changes and no new job was introduced, so an
ancestry-only integration is unnecessary. Protected Mastermind was re-fetched at
2026-10-07T09:27:49Z to a2254b290caa7b422fd93657e44e992152541ca7; its six changed
paths are research-read integration/requirements/tests. Every loaded governing
document remains byte-identical, so the existing procedure corpus remains valid.

Actual live verification has been extended and independently reviewed to require
both new live.js and theme.js bodies consumed by all four public stock pages,
including their changed page asset stamps. Its separate pre-release theme census
at 09:21:13Z found all four pages still loading theme.js?v=a0fdddc2. The existing
fresh session-receipt and actual retained-China-price assertions remain required.
No live release or actual-page outcome is claimed at this checkpoint.

The final source-contract run passed 114 first-frame checks and caught the visual
manifest's stale links to the earlier receipts (PID 90464, exit 1). After actual
browser execution, the repair_extension index was reconciled with the two new
receipt digests and sixteen actual PNG digests, and its generated_at was updated.
All nineteen changed fields are within that extension; historical targets,
operation identity, claims, counts and every other manifest field are preserved.
The corrected manifest SHA256 is
`a668302f1876df0b4219e8b33bcee49631f55d09828965cdf052bef6196c2251`.
The previously failing preservation/index test then passed (PID 4637, 1.11 seconds,
exit 0), as did the same-diff P0B closure gate. No browser assertions or fixtures
were weakened. The final task diff contains 92 explicitly owned paths; hosted
verification and actual release proof remain required.


### Final current-main integrations and release candidate

The earlier e3 integration and final browser evidence were committed as
f5ac25a5425162d48be5ac084d2f87ad550ea8ea. Main then introduced a new, exclusive
research calendar CI owner at 4fc4589f0408fc514599b21a229148a96fb7771f.
Its absolute import-closure check reproduced exactly one missing path,
lib/exchange_holidays.py (PID 25887, exit 1, 131.82 seconds). Adding that one path
made the unchanged absolute gate pass (PID 39661, exit 0, 129.15 seconds).
The new research calendar suite passed all 53 tests (PID 25971, 4.34 seconds).
Independent review verified all 247 job semantics, preserving the previously
accepted steps changes and the retained calendar research projection. That
integration was committed as 58c82c7fa805f4595a7c9740b0c3296490325298.

A further relevant main change, 55e8cf844fbfb851939d5ed91153b4c57ad5edaa,
introduced the default-off integrated-answer API and its dependencies. The sole
deployment conflict was resolved as the exact new main script plus our two
previously accepted calendar comment lines and exchange_holidays restart leaf.
The new main engine/script dependencies and both sets of comments remain intact.
The final deployment script SHA256 is
`daf1fcb26a05a2da951eaeb317a7b87cb004b2dfae825705148792ee740b4b9f`.

The combined manifest preserves all 248 job declarations, including the seven
new-main exclusive API path additions and its new nonexclusive API job, while
retaining every previously accepted holiday path and job step. Existing
duplicate path entries are preserved rather than silently cleaned up.
Its final SHA256 is
`d18541001b88a2599ef222a208eb074db1140ef60ddab96b03e5bb13578e599b`.
The exact semantic comparison passed (PID 89121); the final absolute closure
gate passed (PID 65706, 124.31 seconds); the manifest validator accepted 176
code jobs (PID 90686). Independent review found no additional calendar leaf
required by this API consumer. No other previously accepted task-owned source,
browser receipt, screenshot or fixture blob moved during these integrations.

The actual API restart boundary passed all 253 tests after the final integration
(PID 84182, 12.71 seconds). A supplementary new-API/deployment run initially
passed 60 cases and failed two golden-AAPL cases because the sparse carrier
omitted its committed security and issuer reference tables. Read-only diagnosis
confirmed all eighteen golden package files and all three registry YAML files
were already present. Root materialized only
data/reference/security_master.parquet and data/reference/issuer_master.parquet
from pinned 55e8; both exact blob hashes and byte counts were verified, with zero
tracked content changes and zero provider calls (PID 3330). The same two failed
cases then passed unchanged (PID 4037, 7.97 seconds). No fixture, expectation,
runtime data, calendar source or application behavior was changed for that setup.

At 2026-10-07T09:59:39Z, a fresh origin/main fetch observed
d6b11b5b2f140b7e1c6e004a9bfc132af221f3a0. Its sole delta from integrated 55e8 is
site/stocks/earnings/route-catalog.json, with no holiday source, deployment,
CI or pinned-browser-asset intersection. This generated, disjoint movement
does not require an ancestry-only integration.

The candidate remains BUILT_NOT_PROVEN until the final immutable head has
concluded hosted CI, governed squash integration and actual public release
proof. The parent remains the sole ref/PR/merge/release owner. All read-only
review and browser children have received ACCEPTED / STOP; no child or stale
CI observer owns continuing release work. Next: publish the single final
candidate on PR #8606, update the prepared observer and actual-live verifier
to that exact head, conclude CI, merge through the existing admission law,
verify both served assets/page stamps plus fresh session receipts and actual
retained-China-price witnesses, then write the final PR receipt explicitly
superseding this historical pending-release state.


## CI-definition freshness refresh — 2026-10-07T10:26Z

Main `38f437d50f631ed8cb6e4fecd71d74d6a0402594` changed `.github/ci/legacy-jobs.yml` after candidate `243fd187b1656c3e411481950e8135188a31f8ab` began hosted proof. The canonical `ProofFreshness` rule marks any change under `.github/ci/` stale, so the earlier run cannot authorize this merge. Its archived observation at 10:27:44Z had ten of twelve packs successful, two still running, and the complete contract-delta gate successful; it is not claimed as concluded green.

The root integrated pinned main with a normal conflict-free merge. The only shared owned file movement was the CI manifest: `unrun-factor-research` gained the existing R4 V2 receipt help/test steps, and `unrun-intl-libraries` gained the existing theme-graph probation hierarchy test. An independent read-only reviewer found no new holiday imports or feature overlap. A parsed three-way comparison verified all 248 job declarations and every field against the prior candidate plus exactly those two incoming step lists. The other 91 task-owned blobs remained byte-identical. The integrated manifest SHA256 is `75d68e86615ba8be412c0f04d1895b6edb64ba4569ff81ffcc1e5546b634ac3c`; its normal validate-only gate passes for all 176 code jobs.

The holiday implementation, deployment restart boundary, accepted live/theme asset hashes, canonical HK/Canada browser receipts and historical fixture baseline are unchanged. Their existing proof remains applicable. New hosted CI is required on the refreshed immutable candidate because the CI definition changed. The old read-only observer is stopped before replacing its expected candidate; no GitHub job is manually cancelled and no proof assertion or merger rule is relaxed.

This checkpoint remains **BUILT_NOT_PROVEN**. The parent remains the sole commit/push/merge/release owner and will complete concluded exact-candidate CI, fresh canonical admission, squash merge, served-source and asset verification, fresh session receipts and actual retained China price witnesses before issuing a release receipt.
