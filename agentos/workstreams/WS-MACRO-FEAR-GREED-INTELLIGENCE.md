---
key: MACRO-FEAR-GREED-INTELLIGENCE
title: "Macro Fear & Greed: sentiment, VIX dynamics and independent turning evidence"
objective: >
  Deliver a source-transparent Fear & Greed instrument in Macro Risk Radar and its
  Macro Signals study view, distinguishing sentiment level, VIX velocity and
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
  - templates/fear_greed_intelligence.css
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
  Publish the verified registered workspace branch through a PR, verify
  every binding check and merge, then verify the actual served Macro path.
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
Macro Signals contains the full method and preserves a separately disclosed
legacy comparison. No new state, queue, collector, auth or publication plane.

## Observed results before publication

The feature regression run passed **197 tests**, followed by **3 additional
cache-schema and observation-clock contracts**. The existing broader dashboard
release unit passed **326 tests with 1 skipped**. The actual candidate Macro
dialog/controller passed **131 browser assertions** over desktop/mobile,
English/Chinese and dark/light, with no JavaScript exceptions or horizontal
bounds failures. The mobile navigation text-fit issue identified in visual
review was fixed and now has its own browser assertion.

The canonical capture tool produced **16/16 screenshots** for the summary and
deep specimens. Design-system added-line checks pass with zero blockers; the
visual-evidence guard passes; source/site asset sync passes for **128 pairs**.
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

## Completion frontier

Feature code, current visual evidence, deterministic contracts and the frozen
replay are ready for protected publication. Next: commit this one registered
workspace, reconcile current main, open its PR, verify binding checks, merge and
verify the actual served Macro path. No production deployment has been claimed.

## Action-specific capability evidence

`studio_git_publish_status` returned `TYPED_GIT_PRECHECK_REFUSED / NOT_APPLIED`
for this Macro operation; its exact internal exception is not exposed. Bounded
diagnosis found a repository-selection mismatch: CLI status without `--repository
macro` returns "workspace is not registered to the source repository", whereas
`mmx-workspace status --repository macro --lane web` resolves this exact registered
workspace, branch and HEAD successfully. The status call submitted no modifying
effect. Do not retry that unchanged helper or alter its host configuration.
Normal Macro Git/PR delivery remains within the existing attended host-command
and repository assignment; no permission denial, replacement workspace, writer
lease conflict or uncertain publication effect was observed.
