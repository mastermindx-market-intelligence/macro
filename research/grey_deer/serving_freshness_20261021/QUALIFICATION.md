# Census Risk / Risk Radar serving freshness — 21 October 2026

## Status and source custody

The existing Grey Deer / Risk Radar / Risk On–Risk Off programme, MAS-258, remains **In Progress / MISSION_COMPLETE=false**. This is a continuation of the accepted census and release work, not a replacement programme, a new research trial or a policy promotion.

[Mastermind PR #1660](https://github.com/mastermindx-market-intelligence/Mastermind/pull/1660) merged at 2026-10-21T06:24:13Z: final head `b54c58df73077bf50762e71136d8a8ae6c92bed2`, merge `3960aefcf4724a88812d79d97c1b370dc9f951c4`. Source merge does not establish deployment or installed acceptance. The detailed reader tests/reviews below retain their original predecessor scope. The current source, publisher and MTF frontier is in [the current continuation](CONTINUATION.md).

The admitted source operation is `risk-radar-serving-freshness-20261021`, workspace `/Volumes/Mastermind 2/agent-workspaces/web/risk-radar-serving-freshness-20261021`. The first source checkpoint is `9c967c27e71c49a278fb27b1978b0db678601b47`; its checks do not certify the successor.

The previous Macro evidence carrier [#9595](https://github.com/mastermindx-market-intelligence/macro/pull/9595) is merged at `444140f2446ef2025da07ce1b591e0c0ce4393d4`. Its closed branch must not be reopened. This evidence continuation uses the admitted Macro operation `census-risk-continuation-20261021`, branch `sol/web-census-risk-continuation-20261021`, based on `2fc04b05694bd565c8269f054b1f8418f0045220`.

## Reproduced live defect

A read-only SSH inspection through the existing M2 identity on 21 October observed the running service's mount namespace and made an authenticated loopback GET. Credentials were used only in process memory and were not emitted.

| Observation | Result |
|---|---|
| Installed source marker | `fe7afd0111141bae27927715e709d074fea729e2` |
| Service | active, PID 2884430, restart counter 0 |
| Service activation | 20 October 2026, 10:54:51 UTC |
| GET /api/market_view | HTTP 200 |
| Publication asof | 2026-08-07 |
| Publication built_at | 2026-08-10T22:40:11.583831+00:00 |
| Publication sequence | 9 |
| Risk Radar badge | age_sessions=1, stale=false, status=validated |
| Label comparison | confirmed=true, plane consensus risk_on |
| Response cache | public, max-age=5, stale-while-revalidate=5 |
| Published file SHA256 | `17e4621d51d0b517fa9143214936c89997784ad85fe5779740ebaba7134b5df5` |

The verified file was read through `/proc/<actual-main-pid>/root/opt/mastermind/data/market_view/latest.json`, not the stale host data view. Its bytes, source date and sequence agree with the API. A separate 10-second health request timed out; this is retained as an observation and is not described as a successful health qualification. The market-view request subsequently completed.

Commands: `systemctl show mastermind.service --property=ActiveState --property=MainPID --property=NRestarts --property=ActiveEnterTimestamp`; read `.deployed_git_sha`; authenticated Python urllib GET to the existing loopback route; SHA256 of the service-visible publication. Studio process receipts 1253 and 4521 completed exit 0. No producer, portfolio, nightly, deployment or service restart was invoked.

## Why publication stopped advancing

Installed-source inspection establishes a structural missing publisher:

- The only `market_view.build` call in the installed app/bot/brain source is in `bot.phase2.run`.
- The registry marks Flagship archived.
- Its retained `daily_loop` wrapper exits through the archived-job guard.
- That legacy job is no longer registered.
- The active `autonomous_daily` job does not replace Market View publication.

The installed source check (Studio process 21868, exit 0) evaluated these exact properties in `bot/phase2.py`, `portfolio/registry.py` and `app/scheduler.py`; the same relationships are present at the protected source pin. This explains why waiting for the active portfolio schedule alone cannot repair the displayed publication. It does not prove that a swallowed write failure caused the last August publication; that earlier possibility remains unestablished and is not the accepted diagnosis.

Restoring natural publication is a separate source contract. The bounded principal consultation and inspected source constraints are recorded in [PUBLISHER_CONTRACT.md](PUBLISHER_CONTRACT.md). It must use the existing artifact owner, retain true source clocks, avoid resurrecting a retired book, and qualify effects on existing machine consumers. Do not manually run a portfolio or nightly to manufacture a fresh proof artifact.

## Current display and reasoning contract implemented

The current display and shared reasoning readers reassess one already-published artifact. It does not acquire new evidence, build an artifact, write files or change portfolio policy.

1. Every known plane, and any unsupported additional plane, is checked against its own original source date at one UTC assessment clock. Unknown planes cannot keep a validation badge.
2. A valid published aggregate is preserved exactly only while its original contributor set remains intact. If any contributor expires, the aggregate is unavailable. Surviving eligibility is reported separately; dropping defensive dissent can never manufacture risk-on consensus.
3. The stored aggregate, label comparison and coherence are verified against the untouched original evidence. Missing, contradictory or malformed assertions are withheld rather than repaired into stronger claims. Boolean values cannot impersonate numeric counts or scores.
4. Coherence is withheld when a member of its original fresh directional cohort expires. Historical disagreements remain as published.
5. The original defensive-floor boolean remains historical snapshot evidence. Current assessment availability and scope are explicit; expiry cannot change a previously true protection flag to asserted false.
6. Source asof, built_at, sequence, readings and budget provenance remain unchanged. The brief describes a freshness assessment, not a newly opened/closed/resolved episode or recovery.
7. The route bypasses response caching and successful responses use no-store.
8. Rotation pairs are captured with the producer's tensor read. GET no longer joins a separate, potentially newer tensor into an old publication. Legacy artifacts without captured pairs show no captured pairs.

9. The autonomous/strategist/MCP shared reader uses the same pure projection. Missing or malformed publications produce an explicit unavailable assessment. Compact MCP rows retain source dates.
10. The live typed decision-context summary requires the paired Market View sequence/date/region, stored governor/signal equivalence, regime market-date and hard-label-direction alignment. It withdraws the complete typed summary when the pair is inconsistent, expiry removes included evidence, or an included Neural Web context lacks eligible original health and its own current date budget. It does not reconstruct a more favorable subset.
11. Current callers bind the Market View identity already read, so a publication change during a read cannot mix generations. Explicit historical context formatting remains pure and unchanged.

The producer's existing numerical algorithms and portfolio authority are unchanged. This is current perception-input qualification; it must not be described as display-only or as proof of identical reasoning behavior. No risk policy, episode store, publisher activation or trade authority is introduced. The retired gate and historical journal readers are not passed through today's freshness projection.

## Validation and retained failures

Final local command, in the source workspace, with Python 3.12:

```sh
PYTHONDONTWRITEBYTECODE=1 python3.12 -m pytest \
  tests/test_market_view_serving.py tests/test_market_view.py \
  tests/test_regime_frame.py tests/test_response_cache.py tests/test_web.py \
  tests/test_decision_context.py tests/test_pm_conviction.py \
  tests/test_bot_mcp.py tests/test_strategist.py \
  -o addopts='' -q --maxfail=3 --tb=short
git diff --check
```

**Reader qualification at the recorded fd4a5dc boundary: 263 passed, 1 skipped in 48.22 seconds, exit 0; diff check passed.** Studio process 71515 completed. The skipped test is the existing live-vendor MCP test because no live vendor/regime data is present in the isolated workspace; the new synthetic MCP consumer regression passed. The predecessor b15b9bd passed 201 cases in process 16645; the intermediate current-reader set passed 98 with one skipped in process 67410. The exact CI-pinned Macro dependency, `256c757b3c4f0ec759571c29a30a71387d0a18f8`, supplied only engine/lib to the isolated ignored vendor directory. No production data was copied.

The route/cache regression uses the actual APIRouter with response caching installed, advances the clock on the same publication, and verifies no cached response, unchanged publication file hash and unchanged clocks/sequence. The page cases execute the shipped JavaScript renderer with synthetic API responses; they are not screenshots or browser visual acceptance.

Retain these prior outcomes:

- Initial new tests failed because serving_view did not exist.
- The first implementation's wider focused run had 83 passes and one header failure; no-cache was corrected to no-store.
- The wider web suite initially failed because the isolated checkout lacked the vendored Macro lib. After installing the exact CI dependency it passed 178 cases.
- Independent contract scrutiny identified actual true-to-false defensive release and inconsistent comparison gaining confirmation; new falsifiers reproduced these before repair.
- Intermediate runs of 25 serving/renderer cases and 195 combined cases remain tied to their earlier file states.
- The first independent candidate inspection returned no source before interruption. It is NOT_ACCEPTED as implementation attestation. Its contract disposition was accepted, but must not be relabeled an independent source review.
- The later GitHub-only independent review ACCEPTED the monotone serving contract at b15b9bd for market_view.py lines1664–1875, market_view.html lines364–425 and web.py lines1747–1775. It excluded date-helper, cache exclusion, rotation producer, test execution and production.
- A second GitHub-only principal source consultation confirmed active raw-reader bypasses in autonomous, strategist and MCP, plus a separate raw typed-context channel. The correction at fd4a5dc received a separate ACCEPTED verdict after five exact GitHub file reads across decision_context, shared PM reader/prompt, strategist and MCP wiring. It accepts current eligibility withdrawal, not full reconstruction of probability/trajectory/axis fields from original raw source snapshots; those provenance limits remain outside this boundary. Tests, publisher activation and production were excluded from that review.
- Hosted CI run 39544738739 and CodeQL run 39544735505 were in progress at the earlier fd4a5dc qualification boundary. The final b54c58d source later passed normal checks and merged; see the dated continuation. Prior-head checks retain their own scope.

AgentOS validation in the Macro evidence workspace completed with 0 errors and 174 repository advisory warnings (1,911 records); git diff --check passed. No generated AgentOS views were edited.

## Browser and release gates

The connected browser reaches the real [Market View](https://bot.mastermind-x.com/market_view) route and displays the existing Pro entitlement screen. Authenticated visual acceptance remains open. A temporary synthetic preview server bound only to M2 localhost was unreachable from that connected browser and was terminated; no exposed preview, alternate login or entitlement bypass was created.

The currently approved release was already executed on 20 October. This continuation did not redeploy it. Current strategic state still prohibits autonomous production deployment. Complete source review/CI and a concrete exact-release qualification before seeking the reserved release decision; a source merge does not establish installed behavior.

## Programme boundaries that remain

The accepted 36-ETF / 8,486-session / 305,496-row census remains descriptive. The proposed 532 B0/B1 fits remain NOT_ADMITTED and zero executed. Existing Yahoo model-purpose, FRED, T13 h21, frozen study, warning/recovery, prospective maturity and capital-policy holds remain binding. Preserve the original warning and product carriers and reconcile real current writers before editing overlapping files.

At the earlier reader checkpoint, paid Fabric was not callable and the Executive reader request was not sent. Later review attempts and their distinct denial/admission states are recorded in the dated continuation; no worker acceptance is inferred. Native consultations were bounded principal C3 contract/design judgments. The first Macro workspace acquisition returned NOT_APPLIED; subsequent bounded Git identity/origin/base checks succeeded and the canonical acquisition then succeeded. No allocator or permission rule was changed.

Canonical issue: [MAS-258](https://linear.app/mastermindx/issue/MAS-258/rru-upgrade-cross-region-risk-radar-recovery-and-unified-risk).