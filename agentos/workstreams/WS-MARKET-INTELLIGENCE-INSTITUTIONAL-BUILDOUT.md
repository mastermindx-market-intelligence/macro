---
key: MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
title: "Market-Intelligence Institutional Buildout — owner-preserving integration overlay (Mastermind #1202 / #1258)"
objective: >-
  Deliver the Mastermind #1258 overlay (packages P/N/E/F/R/L/V/I/S) end to end under the
  Chairman's 2026-10-05 Meta-CEO handoff: every package either reaches a merged, blob-verified
  artifact on origin/main, is handed to its lawful incumbent owner with a RESULT on that owner's
  carrier, or is recorded as an exact human/authority gate for the Chairman. Done when the
  Chairman-facing blocker list is the only remaining work.
status: active
program: sector-rotation-intelligence
repos: [macro, terminal, mastermind]
owner: coo-fable
class: adjudication
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - research/product_intelligence_local_delivery/**
  - research/MARKET_INTELLIGENCE_BUILDOUT_CONTINUATION_HANDOFF_*.md
depends_on:
  - WS:ALPHA-INTELLIGENCE-INTEGRATION
decisions:
  - DEC:MI-BUILDOUT-N-PACKAGE-OWNER-IS-TERMINAL-831
discoveries:
  - DSC:KIT-HOST-QUEUE-GATE-IS-MACOS-ONLY
waves:
  - id: W1
    title: Phase A reconcile — read-only census lanes N0 / E0 / L0 (cursor composer-2.5, GLM tier unavailable)
    status: awaiting_ci
    pr: [8501, 8502, 8500]
    next_action: "After the sweeper merges #8501/#8502: bare `git fetch origin main`, then needle blob-verify each pair under research/product_intelligence_local_delivery/ (#8500 already MERGED 2daaf9f1dc8f and verified)."
  - id: W2
    title: "Phase B fronts — N1 Terminal news server child, E1 K3E qualification tests (stacked on #8337), V0 verdict-preservation census"
    status: done
    pr: [8508, 8506]
    depends_on: [W1]
    next_action: "None for this seat: N1 (#832) closed superseded by Terminal #831 (DEC:MI-BUILDOUT-N-PACKAGE-OWNER-IS-TERMINAL-831); E1 #8506 stays DRAFT HOLD-linked to #8337/#8312 with its RESULT on issue #8309; V0 #8508 MERGED 0beebb3bd1f2."
  - id: W3
    title: "Phase B/C gates — I0 integrated-answer gate census, S0 intraday estate census, L2 independent review of #8470's retained-history reader"
    status: awaiting_ci
    pr: [8512, 8511, 8513]
    depends_on: [W1]
    next_action: "After the sweeper merges #8511/#8512/#8513: needle blob-verify on origin/main. L2 verdict already carried to #8470 (comment 6010401522) as independent-review evidence — owner/Sol decide release."
  - id: W4
    title: Records + L3 display-spec freeze (seat judgment) + L3 context-attach build lane
    status: in_progress
    depends_on: [W3]
    next_action: "Freeze the L3 display spec in the seat against templates/sector_central.html.j2:2110-2196, engine/company_theme_exposure/views.py:32-65 and the Terminal CTE route; collision-check Terminal #796, #8412, #8470 and the GMI held PRs by owned path across OPEN PRs before any edit; then one cursor (or GLM, if mini2 is freed) build lane."
  - id: W5
    title: Phase C/D — I composition (gated on accepted H04/H05/H06), S1 registration (gated on product-owner hypothesis acceptance), F2 (gated on C19 reconciliation), R (other owner)
    status: todo
    depends_on: [W4]
    next_action: "Deliver the Chairman blocker list LAST; do not race the gates (see landmines)."
next_action: "Open and merge the W3 records PR (this record, its handoff, the continuation file, DEC + DSC); then start W4 with the L3 display-spec freeze in the seat."
landmines:
  - "Package N is owned by Terminal #831 (Astra, sol/web-ticker-news-r1-20261004-astra-001, DRAFT 'DO NOT MERGE yet', the lawful Macro #8454 child). Never relaunch a Terminal news server lane; #832 is closed superseded and kept only as a cherry-pick reference."
  - "E1 #8506 is stacked on #8337's branch and inherits the #8312/#8337 Sol holds: never `gh pr ready`, label, or merge it from this seat; the E package's living owner is the Fable seat on issue #8309 (MAS-271)."
  - "F2 is frozen behind the C19 original-request reconciliation (req-4a8daf76317cfe92f436991444c58281 on op c19-mas269-exposure-custody-20261004-01a108b6): never retry with a fresh key, invent an intent id, submit an equivalent new root, or transfer the operation to the new umbrella principal."
  - "#1251's additive old-catalog compatibility repair is published at 1cfdf816924d2c2ab58110c9ec0a5d57b1758bb4 — do not duplicate it."
  - "Package I: H04/H06 are BUILT_NOT_ACCEPTED and H05 is ABSENT (I0 census) — no second canonical answer warehouse, no thesis mutation without Alpha Intelligence/event owner acceptance."
  - "Package S: S0 confirmed a distinct gap (not a Trend Persistence reopening — C1-NULL stands); S1 registration only after the product owner accepts the hypothesis, and no outcome scan before registration."
  - "The GLM tier is fleet-unavailable while mini2 sits under its 50 GiB storage guard (49.56 GiB free) and m1 is quarantined; lanes ran on cursor composer-2.5 (ubuntu1/ubuntu2) as a recorded deviation. Never use Claude-native subagents for labor on this program."
  - "The sweeper may update-branch an armed PR and move its head (#8501 5657d3a3 → 03c37e14); a merged head SHA cannot be fetched and a diff against it passes vacuously — verify merges by needle grep on origin/main only."
do_not_redo:
  - "ACK on Mastermind #1202 exists once (comment 6009097528, 2026-10-06 04:05Z) — never re-ACK or re-START."
  - "N0/E0/L0/V0/I0/S0 censuses and the L2 review are ACCEPTED by artifact (seat re-showed every path:line claim on the pinned heads); do not re-census the same questions."
  - "N1 Terminal server child (#832) is CLOSED superseded by #831 — do not rebuild it."
  - "E1 K3E qualification tests (#8506) are ACCEPTED and returned to issue #8309 (comment 6009863135) — do not re-return or re-review."
artifacts:
  - research/product_intelligence_local_delivery/L0_LEADERSHIP_THEME_CONTEXT_RECONCILIATION_2026-10-06.md
  - research/product_intelligence_local_delivery/V0_VERDICT_PRESERVATION_CENSUS_2026-10-06.md
  - research/MARKET_INTELLIGENCE_BUILDOUT_CONTINUATION_HANDOFF_2026-10-06.md
---

## Context

The Chairman handed Mastermind PR #1258 (head `d1a8e672`, OPEN/DRAFT on `master`, protected base
`7eac3ec2`) to a Fable Meta-CEO seat on 2026-10-05 with a fabric-only execution rule: no
Claude-native subagents, GLM Flash 5.3 first, cursor/grok next, Opus last resort. #1258 is the
owner-preserving integration overlay of umbrella #1202 (op
`market-intelligence-institutional-buildout-20261004`, plan PR #1203). It mints no new
authority: every package extends an incumbent owner (Alpha Intelligence, GMI theme graph,
Research Vault, Information→Price, the Terminal), and the overlay's product surfaces are the
ticker/news change view, the expectations/evidence dossier, and the theme/leadership context.

`program:` is the nearest validated key — the sector/cross-sector rotation program that L0/L2/L3
extend; the umbrella itself lives in Mastermind and is cited by PR, not re-created here.

Execution shape: each wave is a set of path-disjoint external lanes (B-kit `remote_lane_v8.sh`
on ubuntu1/ubuntu2, cursor composer-2.5) returning a DRAFT PR; the seat judges every return by
artifact, posts one ACCEPT, marks READY, and arms `merge-on-green` LAST; the sweeper owns the
merge and the seat blob-verifies on `origin/main` afterwards. Program state lives in
`research/MARKET_INTELLIGENCE_BUILDOUT_CONTINUATION_HANDOFF_2026-10-06.md`.
