# MAS-258 release decision preparation

**Disposition at 2026-10-21 12:23 UTC: HOLD — not ready for production authorization.** This is a concrete qualification record for the existing Census / Grey Deer / Risk Radar / Risk On–Risk Off programme. It is not a deployment approval, installation receipt or whole-programme acceptance.

## Actual paired health route — 21 October, 12:15 UTC

The [actual paired route report](ISOLATED_HEALTH_ROUTE_RESULT.json) closes the earlier missing candidate/restored-baseline health witness. It ran once from 12:15:33.753551 to 12:15:59.460655 UTC using the exact previously admitted archive at `87d4af0` and a fresh `fe7afd0` process after complete eligible-code restoration.

| Phase | Observed result | Accepted scope |
|---|---|---|
| Candidate `87d4af0` | Actual request started; no complete response before the independent six-second deadline. Controller deliberately terminated and settled the isolated process group. | Candidate did not establish the isolated six-second contract. No HTTP status, body or precise failure location is inferred. |
| Restored baseline `fe7afd0` | HTTP 200; complete 817-byte response in **5.988967098 seconds**; exact commit, policy and runtime predicates satisfied. | One isolated pass with about **11 ms** margin. It does not clear the prior live timeout or establish production recovery health. |

Both processes registered 18 jobs with the scheduler held paused. The actual service settings and complete frozen health-input files were retained; provider variables used explicitly nonsecret presence fixtures, and configured Codex authentication remained absent. The full FastAPI route, middleware and serialization ran through ASGI without network or provider execution. Both launchers were reaped and groups proved gone before restoration. The ten copied and canonical book/cohort authority hashes, frozen input bytes, service context, Macro dependency source and production identity were unchanged. Final full eligible-code checksum verification found no differences.

The completed baseline read trace records 50 capability-manifest reads, 90 Macro ledger reads and 14 local ledger reads. These counts belong to that baseline observation. The timed-out candidate did not retain a complete request-phase audit/result record; its clean startup audit must not be expanded into a claim of zero later audit events. One cold-process pair does not establish a regression or cause.

C3 accepted the [design, implementation and actual result](ISOLATED_HEALTH_ROUTE_SUMMARY.json). **The experiment completed; the pair did not qualify. Production remains HOLD / NOT_READY.** The exact failed live six-second observation remains unchanged. An identical rerun is not warranted. [Cleanup](HEALTH_ROUTE_CLEANUP.json) removed only completed temporary receivers/archives after preserving full reports, complete frozen health inputs and support receipts.

A later [protected-source comparison](LATER_PROTECTED_SOURCE_DELTA.json) found `7ab47f0b62d9a22ff16a13f6b99b96b681874a93`, two commits beyond the tested archive, changing six session-bridge/documentation/test files and no application, provider or release-helper paths. The actual full-archive qualification stays bound to `87d4af0`; no full-release qualification of that later tip is claimed. Rebind and qualify the actual protected target when a healthy release is ready.

## Candidate and intended result

The candidate repairs current risk serving and the existing natural publication path. Expired or internally inconsistent confirmation is withdrawn by the actual readers. One immutable upstream capture supplies a hash-bound Market View / typed decision-context pair, admitted only when all required voters qualify at their unchanged temporal boundary. The existing macro-refresh job owns the attempt. Trusted initial-prompt evidence is retained through existing decision and journal records; missing historical evidence remains unknown.

| Identity | Bound value |
|---|---|
| Publisher source | Mastermind #1667, `65c071d9d4820135a54d6d2f7af861bb5e7cebc1` |
| Accepted application source | `dd44a6b69587e048a5346387436ab441f1b85512`; current head changes one documentation sentence |
| Previously admitted reader | #1660, landing `3960aefcf4724a88812d79d97c1b370dc9f951c4` |
| Rehearsed composed queue candidate | `87d4af0a152eefa3c5f441f5600fae9133b3deaa` |
| Candidate Git tree | `b329a913d55030e19b038e99a14c9e5ee5bfd998` |
| Complete candidate archive | 104,202,240 bytes; 5,219 members |
| Archive SHA-256 | `ed2c3b671cbe5604cc4c6feb7e9dd387032f870d980021b759d8f481b9dc07cf` |
| Installed baseline | `fe7afd0111141bae27927715e709d074fea729e2` |
| Established cohort SHA-256 | `75d5182d55ffc7e569f50008d9293682cadf56130d42b00eaba23412e2e8585c` |
| Protected admission / final landing binding | Exact protected commit `87d4af0a152eefa3c5f441f5600fae9133b3deaa` and full tree match the actual rehearsal; independently read back at 11:24:02 UTC |

This full composition also includes the existing owners' performance-reader (#1580), instruction-audit (#1669), and provider/scheduler-result (#715) changes. The [bounded compatibility review](COMPOSITION_REVIEW.json) accepts the Risk Radar, custody, startup and release-helper relationships within its stated scope. It does not replace those components' own tests, security checks or admission.

## Evidence already established

Publisher exact-head CI 39580529597 passed all three shards and aggregate 119173199093. CodeQL39580522600 and aggregate 119156961534 passed. Local combined regression passed 472 tests with one existing live-vendor skip under Python 3.12.13. Independent internal source reviews accepted the finite repairs after root reproduced their four initial findings. The failed findings and earlier test results remain bound to their original revisions.

The [composed rehearsal](COMPOSED_REHEARSAL_SUMMARY.json) ran at 10:59:54–11:00:39 UTC against the installed Linux Python 3.12.3 environment. It explicitly imported app.main, the publisher and receipt, three changed provider bridges and two new lazy performance modules from the candidate receiver. Actual registered startup completed with 18 jobs. Resume was held before dispatch, every first-run flag remained false, and no provider, portfolio, performance collection or publication callback ran.

All ten copied book/cohort authority files and their ten canonical counterparts retained their hashes. Live code, canonical data and resolved vendor targets were read-only inside private mount, network and PID namespaces. The child process group was proved absent before complete eligible-code restoration; the final checksum dry run was empty. Production remained fe7afd0 / PID 3972732 / NRestarts 0. The [full report](COMPOSED_REHEARSAL_RESULT.json) has SHA-256 `ada695588a81395030266c393015d2f588082fb641b4177e91fe54487ed24be2`.

The earlier integration rehearsal at da548855 remains separately valid. Neither isolated run attests to natural scheduled publication, real provider semantics, predictive performance or entitled browser delivery.

## Concrete release gates

| Gate | Current evidence | Required closure |
|---|---|---|
| Protected source — PASSED | #1667 merged at 11:21:56 UTC as041b8ab5 after CI39586671816 succeeded. #715 followed at 11:21:57 UTC as87d4af0 after CI39586673741 succeeded. [Independent protected readback](PROTECTED_SOURCE_BINDING.json) proves exact commit/full-tree equality with the actual composed rehearsal, including all24 owned/helper blobs. | No repeat of the identical archive is necessary. Preserve this exact binding; qualify any later material source difference before a release decision. |
| Production health | [The helper-budget observation](COMPOSED_HEALTH_PREFLIGHT.json) failed at 10:57:57 UTC: curl -m6 exited 28 after 6.002257 seconds, zero response bytes, unchanged service identity. The later rehearsal preflight also timed out at 10 seconds. | Resolve the existing health dependency through its incumbent or otherwise establish an accepted current health contract. The earlier200 had no measured duration and does not clear these failures. |
| Reserved deployment decision | Canonical strategic state is PRE_REVENUE_MVP_CONVERGENCE and reserves production deployment. The October 20 approval has already been executed for its earlier release. | Only after the technical gates are concrete and satisfied, present the exact qualified full release for the reserved decision. No new approval is inferred from source publication. |

[Health dependency evidence](HEALTH_DEPENDENCY.json) identifies the installed availability-to-provider-ranking path and repeated Macro ledger reads as a source mechanism, not a sampled-stack attribution of the observed latency. Existing Mastermind #668 owns the lightweight health repair. Its exact head 9a524ada retains a failed CodeQL aggregate reporting six high alerts. Read-only retrieval of that check's six annotations identifies one clear-text storage sink in brain/runlog.py and five clear-text logging sinks in scripts/demo_research.py, dryrun_desk.py, dryrun_diag.py, dryrun_strat_raw.py and review_ticker.py. These sink locations are outside the two changed PR files; that fact does not establish false positives or waive a taint-flow review. The full annotation receipt and finite C3 triage are retained in HEALTH_DEPENDENCY.json. Exact source inspection establishes a boolean presence/authorization path and status-printing script sinks; the generic runlog sink still requires its exact caller/value flow. That narrows the investigation but does not clear an alert, prove successful provider authentication, or establish complete health-route latency. This continuation made no competing patch, source transfer, security waiver, rerun or merge.

## Controlled execution after the gates close

The existing wrapper `scripts/deploy_from_git.sh <full-qualified-SHA>` fetches and requires that exact target to equal current origin/master, then uses a clean complete Git archive. It must refuse a moved target rather than silently deploy another revision. A later material master change needs source/effect qualification before any execution.

Both helpers are unchanged from the accepted fault-matrix source: deploy_from_git.sh blob f40e7895 and deploy_code_to_vps.sh blob f871e888. The helper preserves a complete eligible-code snapshot, refuses unresolved settlement state, binds the established cohort and account/fill preimage, verifies release identity/policy/scheduler health, and verifies complete restoration before recovery restart. Code recovery does not rewind publication, decision evidence or other runtime data. A failed or lost effect must be reconciled on its original carrier.

The failed baseline health observation is also a recovery risk: restoring fe7afd0 code does not establish a healthy rollback destination. Before lifting this HOLD, consume demonstrated recovery health under the applicable six-second contract or explicitly account for the remaining baseline recovery-health limitation in the reserved decision. A later health repair in the target cannot silently qualify the old baseline; any changed helper or release source requires its own exact identity and effect review.

Immediately before any approved execution, rebind current protected source, actual service-namespace identity, pending/WAL/receipt state, nonempty authorities, cohort identity and the accepted health contract. One earlier clean snapshot is not a permanent waiver for changing live state.

## Post-installation acceptance remains necessary

1. Verify installed and service-visible source identity, expected health/policy/scheduler fields, and preservation of book/cohort authorities. Preserve the previous complete recovery snapshot and every failed observation.
2. Read the installed Market View route and declared machine-consumer path. Verify serving-time withdrawal, no-store behavior, per-source clocks and matched typed/publication identity. The old August 7 / built-August 10 / sequence 9 artifact must not regain current confirmation.
3. Observe the existing natural job. The last fixed source read at 10:20 UTC had regime October 20 but MTF August 5. Those bytes must refuse joint publication. A correctly refused natural attempt is useful degraded-state evidence, not a successful new publication. Do not force a manual refresh, nightly, portfolio or publisher run.
4. When the incumbent producer supplies eligible inputs, bind the naturally published pair, actual availability/publication clocks and matching real consumer evidence. Retain initial-prompt-only receipt scope and unknown historical observations.
5. Complete entitled browser delivery and the declared changed-surface matrix: EN/ZH, light/dark, desktop/mobile, long-open/focus-return, failed-fetch/expiry, correction and failed-recovery journeys. The existing Pro boundary is an actual prerequisite; synthetic renderer tests do not substitute for this acceptance.

## Whole-programme frontier

MAS-258 remains In Progress / MISSION_COMPLETE=false. Its [canonical completion criteria](https://linear.app/mastermindx/issue/MAS-258/rru-upgrade-cross-region-risk-radar-recovery-and-unified-risk) require qualified intelligence to reach users and declared machine consumers across the US and ten existing international profiles, with preserved history and evaluation of false alarms and missed rebound.

The [current resequencing](https://github.com/mastermindx-market-intelligence/macro/blob/main/research/grey_deer/GREY_DEER_CONTINUATION_HANDOFF_2026-10-11.md) permits qualified descriptive delivery while predictive power remains unavailable. Accepted GD-3, Gate8 / MAS-36, GD-4A / MAS-37, descriptive census and bounded desktop evidence keep their original scopes. Frozen failed studies are not rerun to obtain a favorable result.

Existing warning, regional, forecast-explanation and Terminal owners retain their product gaps and source custody.

The incumbent census/MTF owner’s 12:17 UTC checkpoint advances the separate source frontier. #9957 remains draft at `26f60b69` after its 12 CI packs passed. Its committed INVALID_ARGUMENT/parent_id report and matched installed validation ordering identify a pre-dispatch schema rejection for actual parent `/root`; original raw response bytes remain unavailable. The facade’s generic retry/absence flags are retained as emitted, not recast as event-specific permission or dispatch evidence. A supported schema-valid representation of the actual immediate parent is still unresolved; no parent substitution, retry, replacement review or source release occurred.

The same owner prepared [six accepted explanation corrections in #9980](https://github.com/mastermindx-market-intelligence/macro/pull/9980), exact `dba0935c5572d550156771d54d3cc7b18d3072ee`. Its reported CI39594838598 passed all 12 packs and gate at 12:09:51 UTC. Independent GitHub metadata confirms it remains open, draft, unlabelled and unmerged. This is prepared source only: prevention acceptance, fresh target/dependency/ledger predicates, canonical application sequencing and an application receipt remain required. Historical eligibility, ledger first-kept decisions and fresh MTF publication are not created by removing six stale explanation fields.

Evidence #9932 remains on its original normal-controller carrier at `146d958`. Its owner reports the 12:12:19 UTC sweep39597422577 deferred refresh with 11 active CI runs against capacity8 after CI definitions changed. Current-definition refresh/admission and fresh-main readback remain open; no manual refresh or capacity override is substituted.

The 532 proposed B0/B1 fits remain NOT_ADMITTED with zero executed. Yahoo model-purpose, FRED and T13 admission holds remain. The accepted first natural W5 issuance is one 30-row SPY batch with immature outcomes, not 30 independent events. Natural maturity, independent evidence and policy costs govern any new predictive or action claim. No new universal score, cohort, numerical authority, automatic exit, policy sizing or provider credential action is part of this release.
