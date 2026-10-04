---
key: TREND-PERSISTENCE
title: Trend Persistence — path-shape evidence family (Mastermind research)
objective: >
  Establish under pre-registration whether the shape of a stock's recent price path (how
  smooth the rise, how deep and how recent its drawdowns) says anything about forward
  return or forward drawdown beyond momentum, volatility and beta, and build an advisory
  profile only if it does. Done = the pre-registered value test read once and its decision
  rule applied.
status: done
program: research-factory
repos: [mastermind]
owner: coo-fable
class: research
blast_radius: reversible
ambiguity: specified
owns_paths:
  - brain/trend_persistence.py
  - research/trend_persistence_*.py
  - research/TREND_PERSISTENCE_*.md
waves:
  - {id: A, title: "Path features, substrate, panel and V1/V2 development experiments (Mastermind PR 1155)", status: done}
  - {id: B, title: "V2 holdout, run once: 29 of 29 confirmed, small; not separated from volatility", status: done, depends_on: [A]}
  - {id: B2, title: "Walk-forward comparison against a volatility-aware model, run once: no model value", status: done, depends_on: [B]}
  - {id: C, title: "Sector, size and group persistence", status: dropped, depends_on: [B2]}
  - {id: D-F, title: "Calibrated profile, shadow snapshot, advisory field", status: dropped, depends_on: [B2]}
decisions:
  - DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-B
discoveries:
  - DSC:IC-GATES-AFTER-RANK-LINEAR-CONTROLS-DO-NOT-SEPARATE-PATH-FEATURES-FROM-VOLATILITY
artifacts:
  - research/TREND_PERSISTENCE_READOUT.md
  - research/data/trend_persistence_b2_result.json
landmines:
  - "Formation dates 2022-07-06 to 2026-06-02 have been scored twice (V2 holdout, B2). No third claim may rest on them."
  - "The B2 one-run guard in the code depends on a local file; the public attempt record on Mastermind PR 1155 is what makes the run single."
  - "Rebuilding the B2 simulated reference over the committed file replaces it with the one-line form, which no longer matches its pin and fails the repository identity check (Mastermind issue 1188). Rebuild to a scratch path."
do_not_redo:
  - "Do not run the V2 holdout or the B2 walk-forward comparison again on real data; both were run exactly once on 2026-10-03 and their results are committed."
  - "Do not edit the V2 or B2 pre-registrations, the four pinned modules, or the committed result and attempt files, and do not change any value in the reference file; a test fails if any pin drifts from the committed result. The reference was re-serialized once after the run, values unchanged (readout section 7)."
  - "Do not build a calibrated profile, shadow snapshot or advisory field from these 29 tests (DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-B, DNR:KILL-TREND-PERSISTENCE-PATH-FEATURE-PROFILE)."
next_action: None. Reopen only under a new pre-registration with new constructions or group persistence, on formation dates after 2026-06-02.
---

## Context

The work lives in the Mastermind repository (`mastermindx-market-intelligence/Mastermind`,
PR 1155, squash-merged as `1c5bc0c3a978`). The full account is
`research/TREND_PERSISTENCE_READOUT.md` there; every number it prints is in a committed
result file under `research/data/`.

It is merged and not deployed. The change adds nothing that runs, and production was 158
commits behind Mastermind `master` when it merged, so a deploy is a release decision for
those other changes, not for this study.

Waves C to F were conditional on the B2 value gates. C also needs point-in-time sector
history for former index members, which does not exist (the current map covers 3 of 1,083).
