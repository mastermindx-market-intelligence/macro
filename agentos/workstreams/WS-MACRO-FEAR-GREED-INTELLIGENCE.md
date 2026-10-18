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
  Complete the genuine CI repairs on PR 9548, observe the repaired exact-head
  checks, merge only on concluded applicable checks, and verify the served Macro
  Risk Radar study through the existing render/publication lane.
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
