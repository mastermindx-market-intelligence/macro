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
repos: [mastermind, macro]
owner: coo-fable
class: research
blast_radius: reversible
ambiguity: specified
owns_paths:
  - brain/trend_persistence.py
  - research/trend_persistence_*.py
  - research/TREND_PERSISTENCE_*.md
  - collectors/sp1500_pit_sectors.py
  - tests/test_sp1500_pit_sectors.py
  - data/breadth/sp1500_pit_sectors.parquet
  - data/breadth/_sp1500_pit_sectors_coverage.json
  - data/breadth/_sp1500_pit_sic_cache.json
waves:
  - {id: A, title: "Path features, substrate, panel and V1/V2 development experiments (Mastermind PR 1155)", status: done}
  - {id: B, title: "V2 holdout, run once: 29 of 29 confirmed, small; not separated from volatility", status: done, depends_on: [A]}
  - {id: B2, title: "Walk-forward comparison against a volatility-aware model, run once: no model value", status: done, depends_on: [B]}
  - {id: C-0, title: "Point-in-time sector substrate for the 1,083 S&P 1500 leavers (macro collector, as-of-now labels, CIK bridge only)", status: done, pr: 8403, depends_on: [B2]}
  - {id: C-1, title: "Wave C pre-registration MERGED in Mastermind (PR 1226, master 521720b09be2, freeze date 2026-10-04 UTC): research/TREND_PERSISTENCE_PREREG_C1.md, development pass C1 on the already-scored dates plus a frozen confirmation C2 on formation dates after the freeze commit", status: done, depends_on: [C-0]}
  - {id: C-2, title: "Instrument research/trend_persistence_group.py and its 18 tests in Mastermind (PR 1230, master 1644ace945a8) against the C1 document section 11 pins, then ONE C1 development run 2026-10-05T00:06Z from the committed clean tree: C1-NULL, three cells scored, none carried (Mastermind PR 1252, master 7eac3ec252475600147ec9a376b8ca16403ac4c5)", status: done, depends_on: [C-1]}
  - {id: C-3, title: "Frozen C2 confirmation: one gating read on formation dates after the freeze once n_read is reached, fixed sequence h20 then h60 then incremental; no re-read - DROPPED: C1-NULL (C1 document section 8) carries no cell, so n_read is null, no constants block exists and no C2 read is ever made", status: dropped, depends_on: [C-2]}
  - {id: D-F, title: "Calibrated profile, shadow snapshot, advisory field", status: dropped, depends_on: [B2]}
decisions:
  - DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-B
  - DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-C
discoveries:
  - DSC:IC-GATES-AFTER-RANK-LINEAR-CONTROLS-DO-NOT-SEPARATE-PATH-FEATURES-FROM-VOLATILITY
artifacts:
  - research/TREND_PERSISTENCE_READOUT.md
  - research/data/trend_persistence_b2_result.json
  - research/TREND_PERSISTENCE_PREREG_C1.md
  - research/trend_persistence_group.py
  - research/data/trend_persistence_c1_attempt.json
  - research/data/trend_persistence_c1_result.json
landmines:
  - "Formation dates 2022-07-06 to 2026-06-02 have been scored three times (V2 holdout, B2, C1 development). No further claim may rest on them."
  - "The B2 one-run guard in the code depends on a local file; the public attempt record on Mastermind PR 1155 is what makes the run single."
  - "Rebuilding the B2 simulated reference over the committed file replaces it with the one-line form, which no longer matches its pin and fails the repository identity check (Mastermind issue 1188). Rebuild to a scratch path."
  - "Every C1 development label exits on or before 2026-06-02 (embargo). Formation dates after the freeze commit belong to the C2 confirmation read alone; the bridge 2026-06-03 to the freeze is printed, never gated (research/TREND_PERSISTENCE_PREREG_C1.md sections 8 and 10)."
  - "The C1 document is frozen at its merge. Any change to a gate, constant, label or construction after that needs a new pre-registration, never an edit; the machine-written constants block (section 11) is the only text the instrument may append."
do_not_redo:
  - "Do not run the V2 holdout or the B2 walk-forward comparison again on real data; both were run exactly once on 2026-10-03 and their results are committed."
  - "Do not edit the V2 or B2 pre-registrations, the four pinned modules, or the committed result and attempt files, and do not change any value in the reference file; a test fails if any pin drifts from the committed result. The reference was re-serialized once after the run, values unchanged (readout section 7)."
  - "Do not build a calibrated profile, shadow snapshot or advisory field from these 29 tests (DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-B, DNR:KILL-TREND-PERSISTENCE-PATH-FEATURE-PROFILE)."
  - "Do not run the C1 development pass again (one-run guard; the public attempt record research/data/trend_persistence_c1_attempt.json pins the single run at master 1644ace945a8) and do not make any C2 read: under C1-NULL no cell carried, n_read is null and no constants block exists (DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-C)."
  - "Do not reopen group persistence by editing research/TREND_PERSISTENCE_PREREG_C1.md; industry-group or industry, basket and dynamic-theme constructions are untested and need a NEW pre-registration document with formation dates after it."
next_action: None pending; the workstream is closed at Wave C under C1-NULL (DEC:TREND-PERSISTENCE-STOPS-AT-WAVE-C). A successor who wants industry-group or industry, basket or dynamic-theme group persistence writes a new pre-registration document in Mastermind first (never an edit of research/TREND_PERSISTENCE_PREREG_C1.md), gated on formation dates after that document merges.
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
