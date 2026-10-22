# Verification record

Executed on 22 October 2026 in the owned Market Navigator source workspace.
This is a bounded foundation record, not whole-product acceptance.

## Source correctness

```
python3 -m pytest tests/test_market_navigator.py tests/test_market_navigator_sources.py \
  tests/test_market_navigator_model_audit.py tests/test_market_navigator_daily_audit.py \
  tests/test_market_navigator_preview.py -q \
  --basetemp=research/market_navigator/.pytest-tmp -o addopts=
```

**89 passed in 8.53 seconds.** Tests cover finite numeric and clock contracts,
future knowledge, revisions, stale nested inputs, unit/subject/horizon mismatches,
explicit invalidation, deadlines, scenario-definition availability and subject binding,
public clocks/conditions/counterevidence without source leakage or mutable aliases,
no implicit lifecycle, no composite score,
owner receipt binding, unsupported subjects, public projection and no authority
escalation. Test fixtures do not prove source authenticity or forecast performance.

## Browser study

```
PYTHONPATH=. python3 scripts/research/market_navigator_browser_check.py \
  --output-dir research/market_navigator/evidence
```

**8 of 8 combinations passed** in Chromium 151.0.7922.34:
1440/390 pixels x English/Chinese x dark/light. Checks include horizontal overflow,
JavaScript exceptions, modal Escape/focus return, comparison toggle, unsupported
horizon abstention, disabled account save and stale/missing states. Screenshots and
machine report are in `evidence/`.

Human-style visual inspection was performed on desktop English dark, mobile English
light and mobile Chinese dark. Their hierarchy, spacing, numeric lanes, readability
and viewport fit were reviewed. Remaining variants have automated layout/interaction
checks, not a claim of independent user usability testing. No native Paper write or
production URL was tested.

## Model and data research

- `MODEL_AUDIT.json`: 224 simulated pre-expiry comparisons; analytic charm finite-
  difference check; 20 of 56 deliberately invalid full-day extrapolations exceed a
  unit delta-change bound. This is model applicability, not market alpha.
- `DAILY_DATA_AUDIT.json`: three official Cboe daily history files, bounded explicit
  foreground acquisition, data cutoff 21 October 2026. VIX1D: 1,114 daily rows,
  78 lows <=6.88, zero closes <=6.88. Daily lows cannot identify intraday trigger
  ordering or joint execution conditions. Raw histories are not committed.
- `SOURCE_ADAPTER_AUDIT.json`: one existing local market-state copy reported
  9 October against a 21 October expected daily floor; missing availability receipt
  prevented promotion of any current verdict. This is not a live-site outage census.
- `BENCHMARK.json`: 200 synthetic local runs, 128 observations/12 scenarios,
  Python 3.14.7 on Darwin arm64. p95 5.4878 ms, payload 79,643 bytes. Network,
  source acquisition, authentication and production latency are excluded.

## Repository contracts

- `python3 scripts/agentos.py validate`: **0 errors**, 182 existing overdue warnings
  across 1,943 records at this baseline.
- `python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --validate-only`:
  **350 job definitions validated**, including the new bounded foundation suite.
  This validates the manifest; it does not claim 350 jobs were executed or passed.
- `git diff --check`: no whitespace errors in the inspected tracked diff.

## Remaining proof obligations

Owner-bound live inputs; safe native Paper designs and exact export; Macro/Terminal
production integration; authenticated save/restore and user isolation; permitted
alert delivery; empirical forecast validation; real user task study; CI and merge
receipts; deployed source and signed-in production browser proof.

Those obligations are not satisfied by local tests, a preview, a plan, or this record.

## W1 continuation verification (22 October 2026)

The extended nine-file Navigator suite passed **145 tests in 5.16 seconds**.
It includes the original foundation plus `test_market_navigator_memory.py`,
`test_market_navigator_measurement.py`, `test_market_navigator_entrypoints.py`
and `test_market_navigator_memory_cli.py`. The separate repository import-pinning
ratchet passed **11 tests in 21.48 seconds** after the new CLI was added.

The trusted-owner subprocess test uses synthetic raw regime data and the actual
incumbent projector, identity builder, capture writer and exact retained reader.
The inspection consumer leaves the fixture store's file/directory contents unchanged;
an absent store remains absent. These tests prove interface behavior, not production
identity, live data rights, real market completeness or predictive performance.

The legacy missing-only reader's missing-root creation behavior was discovered in a
synthetic test. The inspection CLI uses the trusted reader only and does not modify
the legacy owner. A valid opaque snapshot is not falsely rendered as a resolved state.

CI run 39751853416 for the prior head failed on two Navigator script import pins.
Both entrypoints are repaired without extending the baseline or adding a waiver.
The new head still owes its own concluded release checks; no merge is inferred here.

Independent review request `market-navigator-foundation-review-20261022` returned
`backend_unavailable`; one exact original-operation reply read returned
`reply_unavailable`. No accepted runtime ID, START, or review result is established.
No replacement request was made. New source remains awaiting independent acceptance.

The previous eight-case browser study was not rerun because its source did not change.
Native Paper, live data, account save/restore, alert delivery, user study and production
proof remain outstanding. Measurement metadata is not a forecast or trading authority.

## Research intake and frontend boundary continuation

The extended eleven-file suite passed **190 tests in 5.89 seconds**. It includes
`test_market_navigator_research.py` (32 synthetic cases) and
`test_market_navigator_response.py` (13 cases, including the actual Python wire
through the JavaScript consumer). A subsequent changed-consumer check passed
45 tests after tightening canonical-state clock presence.

`CLIENT_BROWSER_REPORT.json` records **10 passed Chromium checks**, zero page errors,
zero observed network requests and zero instrumented browser-storage accesses.
It exercises the actual inert client with a synthetic transport: loading withdrawal,
abort, out-of-order response, exact microsecond cutoff, sanitized failure, no retry,
clear/dispose and authority-false propagation. This is not a deployed endpoint,
production authentication, account save, Paper design or market-data proof.

The analyst intake reuses the incumbent grounded Research Intelligence extractor;
it never calls a model or stores a corpus. Source-revision timing, stable source-bound
claim IDs, complete condition text and externally supplied forecast rulers are checked.
Unknown/incomplete or retrospective claims remain unscoreable as specified. Even
complete fields do not prove semantics, source authenticity, prospective capture or
trial admission. No forecast or trading performance was measured.

The local existing-owner trusted root was absent. A production SSH inspection was
blocked by the tool's safety checks before execution; no retry or alternate carrier
was used for that SSH action. Browser connector tab access separately required an
originating connected-browser context. These observations do not establish a source
outage, and no private source data or credentials were extracted.


## Explicit JavaScript CI ownership repair

The actual hosted plan classified `tests/market_navigator_client_harness.js` as
unowned. The existing Navigator job now names both the client and its harness in
explicit `node --check` commands. The functional Python-to-JavaScript test remains;
this adds syntax/path ownership without suppressing other tests or changing CI policy.
The PR was disarmed and read back OPEN at exact head e6e7fea65d4a32439e1cca4765fe3a30018ee290
before this repair. Source is not pushed into an armed/possibly merged candidate.

The incumbent planner was exercised with a one-path changed-file JSON containing
only `tests/market_navigator_client_harness.js`, with `--changed-from origin/main`.
It selected the Navigator job plus two always-on jobs (3/279), with no unowned-path
warning. This verifies path selection; it is not a claim those three hosted jobs ran.
Plan SHA-256: 4dc67261c3ab37434245afe72023611c66fe7219eda4e0abbb2825453d14c50f


## Upstream release reconciliation

GitHub reported the prior candidate non-mergeable after main advanced. After disarming,
main was fetched and merged on the original workspace; Git resolved the shared
manifest automatically, with no unresolved files. The owned numerical/reader/extractor
modules had no upstream changes in the inspected interval. The complete Navigator
suite was nevertheless exercised on the combined source: **190 passed in 4.25 seconds**.

The Navigator CI block was relocated beside the existing microstructure research job
instead of the shared end-of-file append point. Parsed YAML equality before/after
proved all 350 job definitions semantically unchanged; the manifest validator passed.
This reduces an avoidable concurrent append collision without widening permission,
removing checks or introducing another release owner. Exact new head/run remain GitHub facts.

## CI contract-delta remediation (22 October 2026, follow-on)

The exact-head hosted run 39766825827 at b29552481eb3dcc8622a5e7d2298f31a2c1a6ced failed `contract-delta` because the new Navigator suite was inferred for three unrelated ordinary-change probes. It introduced one 25-weight-second job under templates/index.html, scripts/build_free_content.py and engine/prophet/plan_book.py, exceeding the accepted selection ceilings. The separate ci-pack-3 failure reported `unrun-brain-gateway` timed out after ten minutes during unusually slow Ubuntu dependency acquisition; local evidence does not establish a Navigator test failure or authorize weakening this gate.

The fix curates only the new Navigator job with `scope: exclusive` and 68 scoped paths: six Navigator-owned patterns/identities and 62 exact transitive shared dependencies. The incumbent scope-inference audit computed 85 literal imported/read dependencies and **zero uncovered paths** after curation. A second ancestor-init audit found two extra package initializers, `engine/codex_lane/__init__.py` and `tests/__init__.py`; both were declared and the targeted ancestor census is now empty.

The manifest validator still accepts all 350 job definitions. Direct scope probes show the Navigator job is selected by own engine, client and test changes, and NOT by any of the three offending unrelated probe paths. `git diff --check` passes. This is local ownership/probe evidence; the corrected head still owes hosted contract-delta, CI and gated release outcomes. No ceilings, base tests, production gate or unrelated job timeouts were altered.

Paper was newly inspected from the current Studio carrier: Desktop is connected but the adapter returned `accepted_for_write=false` with catalog mismatch (observed SHA-256 1b9afff4c9bcf6f11f5ca2db301bf25ccdc442025344e2ec402459cedcd6a2db; expected ac18857df0aa6323646333368e5798e7c28de7b4d5f5dc3cb320276e3535daa9). No Paper edit was dispatched, and the oversized active design remains held. Local product save census confirms `lib/user_prefs.py` stores scalar UI/alert preferences and `market_memory_retained_saved.py` is an authorized exact retained-output reader, not a generic market-path storage writer. No substitute store was built.


## Hosted curated-membership CI repair (2026-10-22)

The post-curation hosted CI run 39774043837 at exact head
6ed9008275b15f1cb4de94adbca84403530f9d7b failed one new
control-plane contract: 794 other cases passed, one was skipped,
and test_the_curated_exclusive_set_is_actually_declared rejected
market-navigator-foundation as missing from the existing closed
CURATED_EXCLUSIVE job membership set. This is a separate gate from
the now-fixed ordinary-code packing over-selection; it remains enforced.

The owning branch now adds that job ID to the existing pinned membership
without weakening the assertion, selection ceilings, timeouts or reviews.
Targeted local checks for curated-membership, explicit-scope coverage and
exclusive-scope replacement: 3 passed. The new candidate still owes
hosted CI and independent review. No merge or production claim follows.

## W3 presentation increment (source-only)

The new isolated `templates/market_navigator_view.js` and `.css` are an actual DOM presentation consumer of the incumbent validated response shape, not a newly admitted source. They render condition status, original rule/deadline clocks, support and counterevidence without probabilities or trade effects. Controls switch EN/ZH and dark/light with keyboard focus and disclosure state preserved; a new response/error withdraws old content. `VIEW_BROWSER_REPORT.json` records eight synthetic real Chromium viewports with no observed network/storage, horizontal overflow or browser errors. The Python->JS zero-browser-dependency harness was run under `tests/test_market_navigator_view.py`. These are not Paper, signed-in or production proofs.


## Completed-bar confirmation and composer-to-browser proof (22 October 2026)

The W3 source now implements `engine/market_navigator_price_confirmation.py`,
not a second market regime or data feed. Its exact typed bar/window/receipt
contract prevents a single quote from counting as a crossing or hold. A
completed-bar mathematical event can enter the existing read-only compositor
only via `qualified_observation` with an application-bound source verifier and
a separate derived receipt that cannot extend the original source validity.
The closed output does not expose raw subject/definition/generation references,
and all trade/signal/probability/rank/size/alert flags remain false.

The new `tests/test_market_navigator_price_confirmation.py` passes **64**
synthetic deterministic cases. The cross-layer visual proof now exercises
three synthetic completed swing bars -> event confirmation ratio -> existing
`compose` -> `bind_response` -> exact-request JS validator -> bilingual DOM.
Eight Chromium desktop/mobile, English/Chinese, dark/light cases passed.
The W3 responsive illustrations were regenerated from that test; they remain
synthetic, not signed-in operational evidence. The full local Navigator
target `python -m pytest tests/test_market_navigator*.py -q` passed
**257 tests**. The shared 350-job CI manifest validated, and two scoped
curated-membership/scope tests ran successfully without changing any CI
ceiling, job identity or release gate.

Evidence class: BUILT_NOT_PROVEN. The owner verifier used in synthetic
tests does NOT prove a real source generation. Rights admission, real owner
bar/sequence receipts, operational prices, predictive performance, live
route/mount, Paper-native design, user-account save/restore and release
remain outstanding. Existing PR #10055 and its held independent review
are unchanged by this separate W3 source increment.


## W3 exact instrument/account-scope binding (2026-10-22)

The W3 integration fixes a distinct wrong-instrument response-replay risk:
the initial response/v1 bound instrument identity before publication but
removed it from the browser wire; unrelated controllers could both use
the same local `navigator-1` correlation, horizon and cutoff. New
`market_navigator.response/v2` adds the SHA-256 of the exact request
subject. The request-bound browser consumer computes this digest using
secure-origin WebCrypto before dispatch and rejects mismatched subjects,
extra/missing envelope keys, and old v1 wire. This digest is *correlation*,
NOT an authenticator, entitlement record, audience disclosure permission,
or evidence that the source is current.

A separate `templates/market_navigator_mount.js` is a no-URL,
no-automatic-read, no-storage host interface: the existing authenticated
application must supply the exact subject, time, horizon, principal and
entitlement scope key and its already-admitted source reader. The mounted
component checks that scope before read, after read and before render.
Principal or instrument rebind atomically withdraws prior content, and
a response resolved after scope change cannot be published. Node and
Chromium tests include wrong-subject replay, unavailable WebCrypto,
account switch during transport, absent source, late reply, no
auto-read and visual state withdrawal. The implementation creates no new
authentication, source admission, endpoint, account store or alert owner.

Verification at this W3 candidate before commit:
`python3 -m pytest tests/test_market_navigator*.py -q`: **259 passed**.
`python3 scripts/research/market_navigator_view_browser_check.py
--output research/market_navigator/VIEW_BROWSER_REPORT.json`: **8/8**
Chromium desktop/mobile + EN/ZH + dark/light, using a locally intercepted
secure origin and one synthetic read per permitted activation.
The incumbent legacy CI manifest validator recognizes **350** job
definitions, without adding a new job or relaxing controls. The
existing Navigator job owns both added mount scripts and its two tests.
These checks are synthetic code/browser verification, NOT authenticated
production, Paper-native design, operational market data or a forecast
success record. Source-use scope remains independently gated by the
incumbent owner.


## Investor comprehension: status explanation increment (22 October 2026)

The W3 investor-facing conditional paths now expose an unranked bilingual
diagnosis describing why a scenario is waiting, unresolved, invalidated,
conditions-met, expired, or out of scope. The count uses only the admitted
boolean/null condition results; unknown does not become zero or false, and
no arbitrary trigger is promoted as a preferred action. The expanded exact
conditions, original deadline, source availability and research-only
non-signal status remain available unchanged.

Tests exercise the three distinct fixture paths (conditions met, waiting,
unresolved) in both languages and all eight Chromium layout/theme/view
configurations. This is a readability improvement, not a source, probability,
forecast, recommendation or live-user validation. It remains
BUILT_NOT_PROVEN until authenticated real-path proof is obtained.


## Evidence-family browser matrix (2026-10-22)
The seven canonical evidence families are shown without interpreting
missing evidence as bearish, bullish or a failed forecast. The browser
matrix proves a rendered current price lane, unavailable breadth lane,
and a collapsed disclosure for five wholly unsupplied families.
Validated source values and clocks remain bounded and no new HTTP read
or persistence was added. After adding outcome falsifiers to the
*existing* Navigator CI job, the full focused run passed **310 tests**;
the manifest still validates 350 jobs without creating a job or
widening ordinary PR packing ceilings. Eight independent local Chromium
combinations passed (1440/390, EN/ZH, dark/light) on synthetic data.
The committed screenshots are design/DOM evidence, NOT a Paper-native
file or authenticated production result.


## Observed-versus-estimated investor honesty (2026-10-22)

The existing v2 fixture is copied in the isolated JS unit harness with
a price observation reclassified from quality observed to estimated,
then passed back through the request-bound client validator. The
view explicitly prints `100 USD · estimated` and returns to
`100 USD · observed` after the immutable original state is restored.
The regression also checks that the sole unresolved condition is named,
that absent source categories stay compact, and that no recommendation
or unsupported probability appears. All 310 Navigator tests and eight
desktop/mobile EN/ZH dark/light Chromium tests passed after this change.
These results concern synthetic fixtures only, not production source
receipts or investor comprehension measurement.
