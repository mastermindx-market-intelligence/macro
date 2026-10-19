---
key: MACRO-FEAR-GREED-INTELLIGENCE
title: "Macro Fear & Greed: sentiment, VIX dynamics and independent turning evidence"
objective: >
  Deliver a source-transparent Fear & Greed instrument in Macro Risk Radar and its
  native expanded study disclosures, distinguishing sentiment level, VIX velocity and
  acceleration, data clocks and independent turning evidence. Done requires
  deterministic and bilingual responsive browser proof, protected delivery and
  verification of the served production path, not a claim of predictive alpha.
status: active
program: market-regime-risk
repos: [macro]
owner: sol
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
  - engine/fear_greed_intelligence.py
  - templates/_fear_greed_intelligence.html.j2
  - tests/test_fear_greed_intelligence.py
  - tests/fear_greed_intelligence_browser.py
  - scripts/research_fear_greed_intelligence.py
  - research/FEAR_GREED_INTELLIGENCE_V1.md
  - reports/fear_greed_intelligence/
waves:
  - id: FG1
    title: "One existing-owner producer-to-Risk-Radar vertical, proof and publication"
    status: in_progress
next_action: >
  Qualify the current-head CI-pack-2 SNI sealed-regeneration sidecar repair
  on original PR 9548, publish one reconciled current-main commit after local
  contract tests, then restore protected merge-on-green and verify exact-head
  hosted CI, covering render and served authenticated Risk Radar proof.
landmines:
  - "The legacy machine-consumed dial and existing regime/risk/trade authority stay unchanged."
  - "VIX acceleration is not VVIX. Absolute VIX threshold and liquidity-shock classifier kills remain binding."
  - "The existing equity_pc_ratio column is an SPY/QQQ/IWM chain-volume proxy, NOT the official Cboe equity ratio. Short history is excluded."
  - "A dated coherent sentiment snapshot can lag current VIX by at most two sessions; stale inputs never masquerade as current."
  - "Retrospective revised-observation replay is not point-in-time validation; forecast_validated remains false."
  - "History extends the existing keep-first ledger; never backfill an already observed row or create a second publisher."
  - "Preserve unrelated Risk Radar dialog escaping work, including the initially open PR 9137."
do_not_redo:
  - "Reuse existing fear_greed, vol_velocity, canonical curve functions, Risk Radar controller and publication pipeline."
artifacts:
  - research/FEAR_GREED_INTELLIGENCE_V1.md
  - reports/fear_greed_intelligence/REPLAY.md
  - reports/fear_greed_intelligence/replay.json
  - reports/fear_greed_intelligence/pinned-data-snapshot.json
---

## Authority and custody

Chris's current attended-Web assignment is the project authority. Protected law
pin: Mastermind `3a265caa9b0fe6d93f133bf8176243ae96b0ea0c`. Macro source base:
`9cfa8918b55a1c4735a90f4ca133506baa9d7966`. Registered operation:
`macro-fear-greed-dynamics-20261017`; carrier branch
`sol/web-macro-fear-greed-dynamics-20261017`. No child worker or production job was
submitted. The Executive read was explicitly readonly, not an admission receipt.

Linear projection: MAS-283 (In Progress). It is not admission authority.

Risk Radar is the primary home; Transmission is the causal-context destination.
Risk Radar contains the full method and history in native disclosures. The
customer origin intentionally 404s the admin-only Macro Signals route; this
feature does not reopen or link it. Its existing stylesheet is reused, and the
existing render picker now recognizes the Macro-only component leaves. No new state, queue, collector, auth or publication plane.

## Observed results before publication

The final feature regression run passed **200 tests**, including cache-schema
and observation-clock contracts. The render ownership/scope suite passed **39
tests**, including execution of the actual six-case region picker contract. The existing broader dashboard
release unit passed **326 tests with 1 skipped**. The actual candidate Macro
dialog/controller passed **145 browser assertions** over desktop/mobile,
English/Chinese and dark/light, with no JavaScript exceptions or horizontal
bounds failures. The mobile navigation text-fit issue identified in visual
review was fixed and now has its own browser assertion.

The canonical capture tool produced **16/16 screenshots** for the summary and
deep specimens. Design-system added-line checks pass with zero blockers; the
visual-evidence guard passes; source/site asset sync passes for **127 pairs**.
Agent OS validation reports zero errors. These are candidate-source results,
not merge, deployment or predictive acceptance.

The frozen descriptive replay contains 4,921 common eligible sessions from
2007-03-07 through 2026-10-13, with 56 high-VIX-level, 180 VIX-relief,
144 relief-broadening, 121 stress-broadening and 96 sharp-repricing episodes.
The episode-level report retains tails, next-close sensitivity, thin-era cells,
bootstrap intervals and an unconditional-drift baseline. No rule was retuned to
its outcomes. Stress-broadening episodes often preceded rebounds, illustrating
why an observed pressure state must not become a mechanical short signal.

Pinned inputs produce a **46.9** sentiment snapshot dated **2026-10-14**, clearly
marked two sessions delayed, while VIX dynamics are dated **2026-10-16**. Credit,
breadth and VVIX clocks differ; the UI exposes this. This is source-pin research
evidence, not a claim about the currently served dashboard.

## Current delivery frontier - October 17 recovery

PR **#9548** is the sole delivery carrier. The recovered source candidate is
`54592828c335d461f86d308f424064113098b57b`. Its CI run `39034640285`
concluded with genuine failures, not a deployment or acceptance:

- `contract-delta` and `ci-pack-0`: nine new import-closure edges were absent
  from the existing exclusive jobs. Four jobs needed both
  `engine/fear_greed_intelligence.py` and `engine/vol_velocity.py`;
  `dashboard-render-contract` also needed the frozen research document.
- `ci-pack-6`: the replay entrypoint lacked a repository-root import pin.

This recovery widens those exact existing path declarations and pins direct
script imports to this checkout. It changes no estimator, threshold, source
input, collector, authorization, test exclusion or replay budget. Direct
retention reason: `LOWER_TOTAL_OVERHEAD` for the bounded 18-line repair; no
worker or Executive Job was submitted.

Verified locally after repair: **49 passed in 175.44 seconds**, using
`.venv/bin/python -m pytest -q tests/test_check_script_import_pinning.py
 tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure
 tests/test_fear_greed_intelligence.py`. The replay script also returned its
CLI help when invoked by absolute path from `/tmp`, with no data publication.
The prior 200-feature-test, 39-render-test, 145-browser-assertion and 16-state
visual receipts above remain candidate evidence; they are not a claim of a
fresh production run. The frozen replay retains its ORIGINAL script hash and
source candidate; do not rewrite its provenance to pretend the import-only
repair produced those earlier results.

The PR was visibly disarmed while retaining `merge-blocked` before changing
its head; recovery comment: PR #9548 issuecomment-6243168672. After publishing
all required repairs, re-arm the existing merge backstop and consume the new
exact-head checks. The old red run is not the repaired candidate's verdict.
Do not waive binding checks or use the inactive pilot-base status as a
feature-test failure: the applicable trusted authority context is main.

## Custody and effect facts

Continue this same registered operation and workspace:
`/Volumes/Mastermind 2/agent-workspaces/macro/web/macro-fear-greed-dynamics-20261017`.
No conflicting source writer or uncertain publication effect was observed.
The workspace contains retained ignored test/research outputs; do not remove
or sparsify it as an idle-session cleanup.

The typed `studio_git_publish_status` helper previously refused precheck
without applying an effect because it did not resolve the Macro registration.
`mmx-workspace status --repository macro --lane web` resolves this operation.
Do not retry that unchanged helper. Normal same-workspace Git/PR delivery is
the existing working carrier, not a permission workaround.

A shared origin/main fetch race reported another writer had already advanced
the remote-tracking ref to `9f9e71a8943e9436bfc68acb961b56166fb61d79`.
Readback confirmed that exact ref. No force update, blind fetch retry or new
workspace was used. Only the shared CI manifest overlapped the feature's
changed paths; its unrelated new job declarations are not feature ownership.
The applicable Macro workspace/delivery guides were unchanged at that ref.

## Remaining production proof

The customer origin intentionally 404s the old Macro Signals route; the full
study remains inside Macro Risk Radar, with Transmission as causal context.
Existing admitted caches, stylesheet, controller and publisher remain the only
owners. Prior anonymous HTTP reads returned Macro 200 and gated assets 401;
no authentication, asset entitlement or route policy was changed.

The dedicated Chrome proof tab targets
`/macro.html?fgi_proof=macro-fear-greed-dynamics-20261017`. Its last exact
JavaScript attempt explicitly reported that JavaScript through Apple Events
is disabled. That interaction requires the human Chrome control
View -> Developer -> Allow JavaScript from Apple Events. Do not retry it
without an evidenced permission change or alter the setting programmatically.
The Browser connector separately reported a missing originating extension
context. These facts do not invalidate the completed candidate-source browser
proof, but that proof is not authenticated production acceptance.

Next executable action: publish the repaired candidate on PR #9548, observe
and repair its actual applicable checks, merge when concluded successful,
reuse a covering render and the normal VPS updater, then verify the served
Macro/native disclosures. Preserve any exact pending effect. Update MAS-283
only to the evidence-supported state. **MISSION_COMPLETE: false.**


## October 18 2026 - Current-base integration and conflict custody

The repaired original candidate 58cce8ed and all three successive
controller-integrated heads e08dc4ea, 69c5b16f, e38a85cc passed applicable
exact-head full CI. The merge sweeper subsequently refused the latest head
because main changed check definitions and GitHub reported a real conflict.
This is a merge-content conflict, not a demonstrated feature regression.

The only conflicting file between e38a85ccf88e2eb387eb3a86edd2863036ef27ed
and main 084ac334a2bf4beb76bd22b5bf7d37a8eb93e051 was
.github/ci/legacy-jobs.yml. Two exclusive-job paths blocks contained
independent additions for the Fear/Greed producers and new Intelligence
Workspace imports. Both sets are required. The attended maintainer removed
merge-on-green, verified merge-blocked remained, fetched exact refs and
fast-forwarded the SAME registered branch/workspace to the controller head.
The ordinary no-commit merge is now conflict-free, retaining both import sets
without weakening any check or editing a Fear/Greed model.

All 12 checked core feature assets remain unchanged by the integration.
The scoped staged diff check passes. The whole-repository staged diff check
found two inherited whitespace lines in unrelated site/theme_tree.html; that
main-owned page is not changed here. The focused test verdict must be known
before publishing the source merge. The standard native controller remains the
merge authority. After a verified push, clear the conflict marker and re-arm
merge-on-green, then consume exact-head CI and the covering normal render
and VPS publication, and verify the served native customer path.

MISSION_COMPLETE: false.


## October 18 2026 10:30 UTC - repeated merge conflict and CI transport boundary

Following the prior repair eb555e647b22, additional refreshed head
69e925833031 and 96033575e777 passed full exact-head CI. Automatic main
integration advanced the same PR to f28a75ecf08e6e8dda6ac0c1ec515a14bc78ff23
with base parent 2001b5011f410947d423f5e75f2a2074d1e34155. All twelve
packed CI jobs completed SUCCESS and the trusted authority and fences passed,
but final CI gate failed in run 39099922927. Root cause observed from job
117601131413: GitHub actions/download-artifact reported ECONNRESET while
requesting a signed artifact URL. The final semantic proof correctly refused
to count missing pack fragments as green. This is INFRASTRUCTURE_BLOCKED,
not a demonstrated failing Fear/Greed test; do not waive or rewrite evidence,
or replay the same CI run blindly. A genuinely new integrated source head
will receive its own CI without additional manual retries.

By October 18 10:30 UTC PR #9548 was OPEN, f28a75ec head, merge-on-green and
merge-blocked both present; GitHub marked CONFLICTING. The latest main was
b912fd97827cca925a7123aa2012e9765077f3f7. A read-only virtual merge
identified only .github/ci/legacy-jobs.yml as conflicted. Its one hunk
contained Fear/Greed engine and VIX importer paths on one side, and new
Market Ontology package and BEA GVC imports on the other. These are compatible
additions and must BOTH survive. The maintainer disarmed merge-on-green and
verified the marker change on the exact f28a75ec head before source writes,
fast-forwarded the same registered workspace and began a normal no-commit
merge from main b912fd97. The real merge confirmed only this one conflict;
the resolution retains both sets without changing any checks, feature
thresholds, UI code, publisher or research outputs. A scoped manifest
staged-diff check passed; targeted regression tests are pending.

This is the existing carrier, not a new source workspace, replacement PR,
worker or pipeline. Prior public customer site had no new FGI markup. Keep
MISSION_COMPLETE=false until protected merge, covering existing render,
VPS publication, and real served desktop/mobile proof.


## October 18 2026 23:54 UTC - current CI refusal and repair frontier

At 23:45Z the exact head d481e93f61ca816ca6db1ab96a8ba7fffc944a98
remained OPEN, with both merge-on-green and merge-blocked labels. GitHub run
39120174450 COMPLETED FAILURE: 11 of 12 ci-packs SUCCESS, while pack 2
job 117654304630 failed only SNI regeneration guards test_schk_05 and
test_schk_06; ci-gate correctly refused. Both failures identify an
extra-in-produced .trial_ledger.jsonl.lock under regenerated scratch output.
Exact-base replay at base b912fd97827cca925a7123aa2012e9765077f3f7
reproduced the SAME lockfile failure; the semantic gate still refuses an
authority-changing candidate because this PR must preserve shared CI import
closures. No Fear/Greed engine defect or missing pack transport was shown in
this run. The historic preceding f28a75ec CI gate was a separate ECONNRESET
artifact transport failure, not a basis for overriding this true test red.

Root cause readback: engine/trial_ledger.py deliberately creates a stable
zero-byte .trial_ledger.jsonl.lock via a durable file lock as part of its
append-only ownership transaction. SNI's strict seal tree comparator treated
this persistent lock in the temporary regeneration directory as a sealed
study artifact, even though the committed seal contains only evidence files.
Do NOT delete/unlink the lock or weaken generic full-tree comparison. The
bounded repair in this original registered workspace keeps the ledger owner
untouched, adds a private-regeneration-only inventory exclusion for the
exact zero-byte regular lockfile with an accompanying generated ledger, and
has negative tests for nonempty, symlink and unrelated extra artifacts.
The complete affected suite passed locally: 60 passed in 445.30 seconds
(2026-10-19 00:00Z), with one unrelated pytest cleanup warning for a
temporary Chromium fixture and no failed tests. This includes both original
sealed-regeneration failures, private sidecar anti-vacuity tests, the CI
closure test and Fear/Greed regressions. Normal source publication is now
qualified by the local affected regression verdict, not yet by hosted CI.

The original branch was explicitly disarmed while merge-blocked and its
d481e93f source SHA verified. Fetched main
5b1cbb31e3af00c928b0aa277f105eee19bc917d and ordinary-merged
it into the same worktree with no source conflict. Existing feature
engines, Risk Radar UI, methodologies, replay and publisher are preserved.
Current protected Mastermind law pin refreshed at
bcf4a2f72538682f2fbe4902f6417e59cd038678, compatible schema
mastermind.sol_skillpack.v1 / 1.0.1. No new branch, worker, CI runner,
QLedger writer or production publisher.

Remaining gates: verify local tests, exact remote push, protected merge and
current-head hosted CI, renderer and VPS publication, signed-in customer
Risk Radar acceptance. The separate market-source freshness dependency is
incumbent QLedger market-isolation PR #9556, still unmerged at last check.
MISSION_COMPLETE: false.
