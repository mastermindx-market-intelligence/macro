---
key: NATIVE-CHART-ENGINE
title: Native Chart Engine — portable main-chart API, owned Canvas2D renderer, preserved workflows
objective: >
  Replace only the rented renderer (lightweight-charts 5.2.0) behind the Terminal's own
  chart-engine contract (terminal/lib/chart-engine/api.ts) with an original Canvas2D
  renderer, while every existing workflow (drawings, live bars, bar replay, pane sync,
  indicators, keyboard access) keeps behaving identically. Done means the "mm" engine
  passes the factory-agnostic conformance corpus, ChartPanel runs on it behind a dark-launch
  selector with a one-flag rollback to "lwc", and production renders the same crops.
status: active
program: terminal-charting
repos: [terminal]
owner: ceo-sol
class: build
blast_radius: user_facing
ambiguity: scoped
owns_paths:
  - terminal/lib/chart-engine/**
  - terminal/lib/__tests__/chartEngine*.test.ts
  - terminal/lib/__tests__/lwcAdapter.test.ts
  - docs/chart-engine/**
  - docs/CHART_ENGINE_MASTERPLAN.md
discoveries:
  - DSC:LANE-RECONCILIATION-HOLD-CLOSES-HOST
waves:
  - id: P2-CONTRACT
    title: Portable main-chart contract — api.ts widened, LWC adapter implements it, census + reference-semantics dossier
    status: awaiting_ci
    pr: 969
  - id: P3-RENDERER-LIBRARY
    title: Owned canvas renderer as pure library — model, series, scales, ticks, input, axis gestures, crosshair, paint, keyboard, LOD, snapshot, decorations
    status: awaiting_ci
    pr: 969
    next_action: >
      When Terminal PR 969 merges, open the follow-up PR from branch claude/ce-integrate2-1012
      (decor lane already merged there) against master with the merge-on-green label and
      native auto-merge.
  - id: P3-CHARTPANEL-MIGRATION
    title: Migrate ChartPanel.tsx raw lightweight-charts call sites onto the engine contract (M01 primary series, M02 studies, M03 decorations)
    status: in_progress
    depends_on: [P3-RENDERER-LIBRARY]
    next_action: >
      Harvest the M01/M02/M03 lane branches (claude/ce-m01-1012, -m02-, -m03-), review each
      docs/chart-engine/migration/M0x_*.patch, apply by hand onto ChartPanel.tsx in a worktree,
      then recapture the six ChartPanel evidence crops before running npm test.
  - id: P4-ACCEPTANCE-DARK-LAUNCH
    title: Conformance corpus green on "mm", engine selector dark launch, production crops, rollback drill
    status: todo
    depends_on: [P3-CHARTPANEL-MIGRATION]
landmines:
  - >
    Editing terminal/components/ChartPanel.tsx reds `npm test` until the six evidence crops
    are recaptured; lanes therefore only ever run the chart-engine vitest subset.
  - >
    Lanes never edit ChartPanel.tsx, lib/paneSync.ts or lib/chart-engine/index.ts; one
    integration session is the single writer and lanes return PROPOSED_PATCHES instead.
  - >
    No `lightweight-charts` import may appear in lib/chart-engine/api.ts or lib/chart-engine/canvas/;
    the integration merge script refuses the lane otherwise.
do_not_redo:
  - >
    The 24 wave-1/2 lanes and the decor lane are merged and deterministically accepted
    (Terminal PR 969 plus branch claude/ce-integrate2-1012); do not re-run their packets.
  - >
    The C02 contract widening forced typing fixes on the paneSync and conformance test fakes
    (Terminal commits ca17729c6 and 8fb010a91); extend those fakes when api.ts grows instead
    of rewriting them.
artifacts:
  - docs/CHART_ENGINE_MASTERPLAN.md
  - docs/chart-engine/
  - terminal/lib/chart-engine/
next_action: >
  Confirm Terminal PR 969 merged, then open PR2 from claude/ce-integrate2-1012 (cc140a0b3: decor,
  ACCEPT, M01/M02/M03 tests+patches, REVIEW) with merge-on-green and native auto-merge; deploy each
  merged master with the git-gated build. Then fan out a Grok/GLM wave for the four P1 review
  findings (F-01..F-04) and the ACCEPT gaps, and hand-rebase the M01 -> M02 -> M03 ChartPanel
  patches with the six-crop recapture as a separate PR.
---

# Native Chart Engine

Programme of record: `docs/CHART_ENGINE_MASTERPLAN.md` in the Terminal repository, produced
from the Chairman's masterplan archive of 2026-10-11. The renderer is replaced behind the
contract, never the product: `ChartPanel.tsx` keeps every workflow and the `lwc` engine
stays selectable as the rollback path throughout.

Delivery runs as fabric lanes (grok-4.6 and glm-5.3, never native Claude subagents) that each
own a bounded package, commit to `claude/ce-<pkg>-1012`, prove a mutant falsifier RED→GREEN,
and return a RESULT.md that the integration session digests before merging `--no-ff`.
