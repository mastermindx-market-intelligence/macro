---
key: MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
title: "Market-Intelligence Institutional Buildout — owner-preserving integration overlay (Mastermind #1202 / #1258)"
objective: >-
  Deliver the Mastermind #1258 overlay (packages P/N/E/F/R/L/V/I/S) end to end under the
  Chairman's 2026-10-05 Meta-CEO handoff: every package either reaches a merged, blob-verified
  artifact on origin/main, is handed to its lawful incumbent owner with a RESULT on that owner's
  carrier, or is recorded as an exact human/authority gate for the Chairman. Done when the
  Chairman-facing blocker list is the only remaining work.
status: blocked
blocked_by:
  - "Package I build: H04/H06 acceptance records + an H05 artifact (owners WS:EARNINGS-INTELLIGENCE-OS, WS:FUNDAMENTAL-FORENSICS, WS:FINANCIAL-INTELLIGENCE-FABRIC) — DEC:MI-BUILDOUT-I-ROUTE-WAITS-FOR-ALL-FOUR-LEGS"
  - "Package S2 registration: product-owner acceptance of the S1 proposal (delta=0.10, n=120, 2027 session-calendar extension first)"
  - "Package F2: C19 original-request reconciliation (req-4a8daf76317cfe92f436991444c58281)"
  - "Packages N / R / P: incumbent owners (Terminal #831, Vault seat 0e657eec, Chairman)"
  - "Package E: K3E owner rulings on the provider-family seam (yfinance->yahoo, E0 #8502) and withdrawn/stale expectation semantics"
  - "Package L history receipts: #8470 retained-history reader release (owner/Sol)"
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
  - DEC:MI-BUILDOUT-I-ROUTE-WAITS-FOR-ALL-FOUR-LEGS
  - DEC:MI-BUILDOUT-I-COMPOSER-READS-PRODUCT-ARTIFACTS-BY-REFERENCE
discoveries:
  - DSC:KIT-HOST-QUEUE-GATE-IS-MACOS-ONLY
  - DSC:CONTRACT-DELTA-TRIPS-TWICE-ON-NEW-MODULE-PLUS-NEW-SUITE
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
    next_action: "None for this seat: N1 (#832) closed superseded by Terminal #831 (DEC:MI-BUILDOUT-N-PACKAGE-OWNER-IS-TERMINAL-831); E1 #8506 adopted by this seat once #8337/#8312 merged and #8309 closed, merged with origin/main, enrolled in intelligence-registry and MERGED 83ccfe82da34; V0 #8508 MERGED 0beebb3bd1f2."
  - id: W3
    title: "Phase B/C gates — I0 integrated-answer gate census, S0 intraday estate census, L2 independent review of #8470's retained-history reader"
    status: done
    pr: [8512, 8511, 8513]
    depends_on: [W1]
    next_action: "None: #8512 5dc3aaf93827, #8511 17acb9646869, #8513 24b77abbccc2 MERGED and blob-verified (2026-10-06 06:58Z); L2 verdict carried to #8470 (comment 6010401522) — owner/Sol decide release."
  - id: W4
    title: Records + L3 display-spec freeze (seat judgment) + L3 context-attach build lane
    status: done
    pr: [8518, 8519]
    depends_on: [W3]
    next_action: "Live proof owed (render lane owns the bake; never cancel/re-dispatch): once the covering render for 1f823f6c5bcc concludes (run 37451035359, queued behind 37436808640), a served basket page such as /basket/semicap_equipment.html must reference the rebuilt CSS hash and the lrc receipt JS. Merge facts: records #8518 c6792267c60f and L3 #8519 (head 0e7911f704ad7818236bee52425087c522cfdd87, squash 1f823f6c5bcc9aa232a7c7bc18cf63112f819a0f) MERGED and blob-verified on origin/main."
  - id: W5
    title: Phase C/D — I composition (gated on accepted H04/H05/H06), S1 registration (gated on product-owner hypothesis acceptance), F2 (gated on C19 reconciliation), R (other owner)
    status: done
    pr: [8517, 8528, 8529]
    depends_on: [W4]
    next_action: "None: I1 spec #8517 f1cd5d9cbd5f, S1 proposal #8528 (head fd56364b7e9303ac11ad7548ce226e0b5cf34791, squash 52fcb1dc1b6e5bd8e7fb7a1e8a0e38863e516308) and V1 verdict preservation #8529 (head 56ad83f4c22045fe45f9c42c625b4becd17eba0a, squash 3af2f39752e7046a4a7996b21ea5467ab90b1192) MERGED and blob-verified; V1 rendered-page proof owed: after the covering render, site/measurement.html on origin/main carries id=\"vp-section\". Every remaining package is owner-gated (W6)."
  - id: W6
    title: Owner-gated remainder — I build, S2 registration, F2, L history receipts, N/E/R/P handbacks
    status: todo
    depends_on: [W5]
    next_action: "Resume only on a named gate opening (blocked_by list); the Chairman blocker list in the program file section 8 names each gate and its owner."
    wait:
      kind: external_action
      review_after: 2026-10-13
      condition: "H04/H06 acceptance + H05 artifact; product-owner S1 acceptance; C19 reconciliation; #8470 release; incumbent-owner handbacks"
next_action: "Seat-buildable scope is exhausted on today's main: deliver the Chairman blocker list (program file section 8), then resume W6 only when a blocked_by gate opens — never re-census, re-spec, or rebuild W1-W5."
landmines:
  - "Package N is owned by Terminal #831 (Astra, sol/web-ticker-news-r1-20261004-astra-001, DRAFT 'DO NOT MERGE yet', the lawful Macro #8454 child). Never relaunch a Terminal news server lane; #832 is closed superseded and kept only as a cherry-pick reference."
  - "E1's nine strict-xfail GAP-E-* tests (tests/test_k3e_provider_family_qualification.py, tests/test_k3e_semantic_seam_qualification.py, intelligence-registry job) go RED as a strict XPASS the moment an owner closes the matching gap: the PR that closes a gap flips its xfail in the same change; never relax strict."
  - "F2 is frozen behind the C19 original-request reconciliation (req-4a8daf76317cfe92f436991444c58281 on op c19-mas269-exposure-custody-20261004-01a108b6): never retry with a fresh key, invent an intent id, submit an equivalent new root, or transfer the operation to the new umbrella principal."
  - "#1251's additive old-catalog compatibility repair is published at 1cfdf816924d2c2ab58110c9ec0a5d57b1758bb4 — do not duplicate it."
  - "Package I: H04/H06 are BUILT_NOT_ACCEPTED and H05 is ABSENT (I0 census) — no second canonical answer warehouse, no thesis mutation without Alpha Intelligence/event owner acceptance."
  - "Package S: S0 confirmed a distinct gap (not a Trend Persistence reopening — C1-NULL stands); S1 registration only after the product owner accepts the hypothesis, and no outcome scan before registration."
  - "The GLM tier is fleet-unavailable while mini2 sits under its 50 GiB storage guard (49.56 GiB free) and m1 is quarantined; lanes ran on cursor composer-2.5 (ubuntu1/ubuntu2) as a recorded deviation. Never use Claude-native subagents for labor on this program."
  - "The sweeper may update-branch an armed PR and move its head (#8501 5657d3a3 → 03c37e14); a merged head SHA cannot be fetched and a diff against it passes vacuously — verify merges by needle grep on origin/main only."
  - "Opus orchestrators (Chairman 2026-10-05) administer fabric lanes for THIS program only; they never spawn native children, never post to carriers, label, ready or merge — seat-only acts stay with the seat. A ROUTE orchestration commission needs the literal line-start label RETURN: (model_routing_guard HEADER_RE)."
  - "The sweeper left five concluded-green armed PRs unmerged for 1-2.5 h on 2026-10-06; merge by hand on the exact head (gh pr merge --squash --match-head-commit) after a same-invocation state read + hold grep, and treat a hold-pattern hit inside your own ACCEPT comment quoting another PR as a false positive to re-judge, not a hold."
  - "A PR adding a new engine/*.py plus a new tests/test_*.py trips contract-delta TWICE: every scope: exclusive job whose inferred closure reaches the importer must declare the new module in paths:, AND the new suite must be named by a run: step (DSC:CONTRACT-DELTA-TRIPS-TWICE-ON-NEW-MODULE-PLUS-NEW-SUITE) — run python3 scripts/check_contract_delta.py --base origin/main (about 3.5 min) before READY; V1 #8529 fixed both before arming, L3 #8519 was armed RED for both."
  - "An armed PR whose checks already concluded can still go CONFLICTING when main edits an adjacent .github/ci/legacy-jobs.yml run line (#8519, 2026-10-06): heal with a keep-both merge of origin/main (never rebase/force), re-run contract-delta, then disarm comment -> push -> ls-remote verify -> re-arm comment -> label LAST."
do_not_redo:
  - "ACK on Mastermind #1202 exists once (comment 6009097528, 2026-10-06 04:05Z) — never re-ACK or re-START."
  - "N0/E0/L0/V0/I0/S0 censuses and the L2 review are ACCEPTED by artifact (seat re-showed every path:line claim on the pinned heads); do not re-census the same questions."
  - "N1 Terminal server child (#832) is CLOSED superseded by #831 — do not rebuild it."
  - "E1 K3E qualification tests (#8506, head 5cc73fa26127, squash 83ccfe82da34) are MERGED and enrolled in the intelligence-registry job — do not re-return, re-review, or re-enrol."
  - "Wave 1-3 PRs #8500/#8501/#8502/#8508/#8511/#8512/#8513 and records #8515 are MERGED + blob-verified — never reopen, re-merge, or re-verify without a material invalidator."
  - "L3 display spec is FROZEN (seat, 2026-10-05, l3_ruling.txt: engine/leadership_receipt.py + 3-line attach + .lrc- panel, anchors disjoint from PR #7870) — do not re-freeze or re-spec; repair rounds amend the lane packet, not the spec."
  - "I1 composition spec (#8517 f1cd5d9cbd5f) is MERGED and its section 8 Q7/Q9 are DECIDED (DEC:MI-BUILDOUT-I-ROUTE-WAITS-FOR-ALL-FOUR-LEGS, DEC:MI-BUILDOUT-I-COMPOSER-READS-PRODUCT-ARTIFACTS-BY-REFERENCE) — do not re-spec, re-census, or re-ask Q7/Q9; Q1/Q2/Q8 -> WS:EARNINGS-INTELLIGENCE-OS, Q3 -> WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2, Q4 -> WS:FUNDAMENTAL-FORENSICS, Q5 -> WS:FINANCIAL-INTELLIGENCE-FABRIC, Q6 -> WS:GMI-THEME-GRAPH."
  - "L3 leadership receipt (#8519, head 0e7911f704ad7818236bee52425087c522cfdd87, squash 1f823f6c5bcc9aa232a7c7bc18cf63112f819a0f) is MERGED — engine/leadership_receipt.py + scripts/build_theme_detail.py attach + .lrc- panel in templates/basket_detail.html.j2 + tests/test_leadership_receipt.py; do not rebuild, re-spec, or re-wire."
  - "V1 verdict preservation (#8529, head 56ad83f4c22045fe45f9c42c625b4becd17eba0a, squash 3af2f39752e7046a4a7996b21ea5467ab90b1192) is MERGED — config/verdict_preservation_registry.json (8 rows, exactly one actual C2) + engine/verdict_preservation.py + #vp-section on the Calibration Lab; display tier only, Trend Persistence C1-NULL stays closed; do not rebuild or re-pin."
  - "S1 theme-relative intraday hypothesis proposal (#8528, head fd56364b7e9303ac11ad7548ce226e0b5cf34791, squash 52fcb1dc1b6e5bd8e7fb7a1e8a0e38863e516308) is MERGED — research only; S2 registration needs product-owner acceptance of its section 0 ask first; no outcome scan before registration."
artifacts:
  - research/product_intelligence_local_delivery/L0_LEADERSHIP_THEME_CONTEXT_RECONCILIATION_2026-10-06.md
  - research/product_intelligence_local_delivery/N0_TICKER_NEWS_TASK_MATRIX_2026-10-06.md
  - research/product_intelligence_local_delivery/E0_EXPECTATIONS_ACCEPTANCE_PATH_2026-10-06.md
  - research/product_intelligence_local_delivery/I0_INTEGRATED_ANSWER_GATE_CENSUS_2026-10-06.md
  - research/product_intelligence_local_delivery/S0_INTRADAY_ESTATE_CENSUS_2026-10-06.md
  - research/product_intelligence_local_delivery/L2_ROTATION_READER_REVIEW_2026-10-06.md
  - research/product_intelligence_local_delivery/V0_VERDICT_PRESERVATION_CENSUS_2026-10-06.md
  - research/product_intelligence_local_delivery/I1_INTEGRATED_ANSWER_COMPOSITION_SPEC_2026-10-06.md
  - research/product_intelligence_local_delivery/S1_THEME_RELATIVE_INTRADAY_HYPOTHESIS_PROPOSAL_2026-10-06.md
  - engine/leadership_receipt.py
  - engine/verdict_preservation.py
  - config/verdict_preservation_registry.json
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
