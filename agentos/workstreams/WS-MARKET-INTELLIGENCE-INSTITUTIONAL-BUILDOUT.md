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
    status: done
    pr: [8501, 8502, 8500]
    next_action: "None: #8500 2daaf9f1dc8f, #8501 59b83048bd3d, #8502 882c03c3c4c2 all MERGED and blob-verified on origin/main (2026-10-06 06:58Z)."
  - id: W2
    title: "Phase B fronts — N1 Terminal news server child, E1 K3E qualification tests (stacked on #8337), V0 verdict-preservation census"
    status: done
    pr: [8508, 8506]
    depends_on: [W1]
    next_action: "None for this seat: N1 (#832) closed superseded by Terminal #831 (DEC:MI-BUILDOUT-N-PACKAGE-OWNER-IS-TERMINAL-831); E1 #8506 stays DRAFT HOLD-linked to #8337/#8312 with its RESULT on issue #8309; V0 #8508 MERGED 0beebb3bd1f2."
  - id: W3
    title: "Phase B/C gates — I0 integrated-answer gate census, S0 intraday estate census, L2 independent review of #8470's retained-history reader"
    status: done
    pr: [8512, 8511, 8513]
    depends_on: [W1]
    next_action: "None: #8512 5dc3aaf93827, #8511 17acb9646869, #8513 24b77abbccc2 MERGED and blob-verified (2026-10-06 06:58Z); L2 verdict carried to #8470 (comment 6010401522) — owner/Sol decide release."
  - id: W4
    title: Records + L3 display-spec freeze (seat judgment) + L3 context-attach build lane
    status: in_progress
    depends_on: [W3]
    next_action: "L3 spec FROZEN (seat); build lane mi_l3_leadership_receipt_r1 RUNNING under the ORCH-L3 Opus orchestrator (cursor composer-2.5, ubuntu1, branch claude/mi-l3-leadership-receipt-20261006). On return: judge by artifact (T1-T6, 8 evidence PNGs, forward-only design gates), READY, one ACCEPT, merge on concluded checks with --match-head-commit, blob + live verify. Wave-3 records #8515 MERGED ca8412f74171."
  - id: W5
    title: Phase C/D — I composition (gated on accepted H04/H05/H06), S1 registration (gated on product-owner hypothesis acceptance), F2 (gated on C19 reconciliation), R (other owner)
    status: in_progress
    depends_on: [W4]
    next_action: "I1 read-only composition spec RUNNING under ORCH-I1 (cursor, ubuntu2, branch claude/mi-i1-composition-spec-20261006); judge against I0's exact gate states (H01 ACCEPTED, H04/H06 BUILT_NOT_ACCEPTED, H05 ABSENT). S1 / F2 / R stay gated by their owners; deliver the Chairman blocker list LAST."
next_action: "Judge the ORCH-L3 (L3 build) and ORCH-I1 (I1 spec) returns by artifact, then READY -> one ACCEPT -> merge on concluded checks -> blob/live verify; carry L3 by reference to #8324 and #8470 / Mastermind #1194; one wave-boundary checkpoint on #1258; Chairman blocker list LAST."
landmines:
  - "Package N is owned by Terminal #831 (Astra, sol/web-ticker-news-r1-20261004-astra-001, DRAFT 'DO NOT MERGE yet', the lawful Macro #8454 child). Never relaunch a Terminal news server lane; #832 is closed superseded and kept only as a cherry-pick reference."
  - "E1 #8506 is stacked on #8337's branch and inherits the #8312/#8337 Sol holds: never `gh pr ready`, label, or merge it from this seat; the E package's living owner is the Fable seat on issue #8309 (MAS-271)."
  - "F2 is frozen behind the C19 original-request reconciliation (req-4a8daf76317cfe92f436991444c58281 on op c19-mas269-exposure-custody-20261004-01a108b6): never retry with a fresh key, invent an intent id, submit an equivalent new root, or transfer the operation to the new umbrella principal."
  - "#1251's additive old-catalog compatibility repair is published at 1cfdf816924d2c2ab58110c9ec0a5d57b1758bb4 — do not duplicate it."
  - "Package I: H04/H06 are BUILT_NOT_ACCEPTED and H05 is ABSENT (I0 census) — no second canonical answer warehouse, no thesis mutation without Alpha Intelligence/event owner acceptance."
  - "Package S: S0 confirmed a distinct gap (not a Trend Persistence reopening — C1-NULL stands); S1 registration only after the product owner accepts the hypothesis, and no outcome scan before registration."
  - "The GLM tier is fleet-unavailable while mini2 sits under its 50 GiB storage guard (49.56 GiB free) and m1 is quarantined; lanes ran on cursor composer-2.5 (ubuntu1/ubuntu2) as a recorded deviation. Never use Claude-native subagents for labor on this program."
  - "The sweeper may update-branch an armed PR and move its head (#8501 5657d3a3 → 03c37e14); a merged head SHA cannot be fetched and a diff against it passes vacuously — verify merges by needle grep on origin/main only."
  - "Opus orchestrators (Chairman 2026-10-05) administer fabric lanes for THIS program only; they never spawn native children, never post to carriers, label, ready or merge — seat-only acts stay with the seat. A ROUTE orchestration commission needs the literal line-start label RETURN: (model_routing_guard HEADER_RE)."
  - "The sweeper left five concluded-green armed PRs unmerged for 1-2.5 h on 2026-10-06; merge by hand on the exact head (gh pr merge --squash --match-head-commit) after a same-invocation state read + hold grep, and treat a hold-pattern hit inside your own ACCEPT comment quoting another PR as a false positive to re-judge, not a hold."
do_not_redo:
  - "ACK on Mastermind #1202 exists once (comment 6009097528, 2026-10-06 04:05Z) — never re-ACK or re-START."
  - "N0/E0/L0/V0/I0/S0 censuses and the L2 review are ACCEPTED by artifact (seat re-showed every path:line claim on the pinned heads); do not re-census the same questions."
  - "N1 Terminal server child (#832) is CLOSED superseded by #831 — do not rebuild it."
  - "E1 K3E qualification tests (#8506) are ACCEPTED and returned to issue #8309 (comment 6009863135) — do not re-return or re-review."
  - "Wave 1-3 PRs #8500/#8501/#8502/#8508/#8511/#8512/#8513 and records #8515 are MERGED + blob-verified — never reopen, re-merge, or re-verify without a material invalidator."
  - "L3 display spec is FROZEN (seat, 2026-10-05, l3_ruling.txt: engine/leadership_receipt.py + 3-line attach + .lrc- panel, anchors disjoint from PR #7870) — do not re-freeze or re-spec; repair rounds amend the lane packet, not the spec."
artifacts:
  - research/product_intelligence_local_delivery/L0_LEADERSHIP_THEME_CONTEXT_RECONCILIATION_2026-10-06.md
  - research/product_intelligence_local_delivery/N0_TICKER_NEWS_TASK_MATRIX_2026-10-06.md
  - research/product_intelligence_local_delivery/E0_EXPECTATIONS_ACCEPTANCE_PATH_2026-10-06.md
  - research/product_intelligence_local_delivery/I0_INTEGRATED_ANSWER_GATE_CENSUS_2026-10-06.md
  - research/product_intelligence_local_delivery/S0_INTRADAY_ESTATE_CENSUS_2026-10-06.md
  - research/product_intelligence_local_delivery/L2_ROTATION_READER_REVIEW_2026-10-06.md
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
