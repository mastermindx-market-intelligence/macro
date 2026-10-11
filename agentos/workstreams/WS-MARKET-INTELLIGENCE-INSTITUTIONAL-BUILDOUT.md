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
  - DEC:MI-BUILDOUT-I-ROUTE-WAITS-FOR-ALL-FOUR-LEGS
  - DEC:MI-BUILDOUT-I-COMPOSER-READS-PRODUCT-ARTIFACTS-BY-REFERENCE
  - DEC:MI-BUILDOUT-N-MERGES-INERT-ACTIVATION-IS-AN-OPERATOR-FLAG
  - DEC:TICKER-NEWS-ALPACA-BENZINGA-RIGHTS-BASIS
  - DEC:VPS-ALPACA-PAIR-REFRESHED-FROM-REPO-SECRETS-BY-DISPATCH-WORKFLOW
  - DEC:MM-IDENTITY-INGEST-IDEMPOTENT-OVER-CAPTURED-DATES
  - DEC:MM-PIT-UNOWNED-PARENT-FSYNC-EACCES-IS-TOLERATED
  - DEC:TICKER-NEWS-UNIVERSE-STAYS-FAIL-CLOSED-ON-UNRESOLVED-ALIAS
  - DEC:PRODUCTION-RECORDS-ROW-BOUND-STAYS-FAIL-CLOSED-UNTIL-PREREG-V2
discoveries:
  - DSC:KIT-HOST-QUEUE-GATE-IS-MACOS-ONLY
  - DSC:CONTRACT-DELTA-TRIPS-TWICE-ON-NEW-MODULE-PLUS-NEW-SUITE
  - DSC:PSKY-SKYD-RENAME-IS-ONE-CIK-DATED-BOUNDARY
  - DSC:MASSIVE-REST-OPTIONS-SNAPSHOT-NOT-ENTITLED-ON-STOCK-PLAN
  - DSC:A-VENUE-MOVING-RENAME-MISSES-THE-COMMITTED-LISTING-KEY
  - DSC:DEPTH-ONE-DEPLOY-CLONE-DEFEATS-ANCESTRY-CHECKS
  - DSC:VPS-ALPACA-CREDENTIALS-SILENTLY-REJECTED-SINCE-2026-08-04
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
    title: "Owner-gated remainder, cleared under the Chairman's 2026-10-07 autonomy directive: S2 registration, E2 K3E refusal semantics, L reader follow-ups, V1 follow-ups"
    status: done
    pr: [8567, 8583, 8587, 8588]
    depends_on: [W5]
    next_action: "None: S2 #8567 aa1ab61ee655, E2 #8583 4f31830b99c3, #8587 c283c1ceaa6e and #8588 e3cb5b86a516 are MERGED and blob-verified (2026-10-07). The served measurement.html check for #8588 is owed to the next covering engine-render."
  - id: W7
    title: "Default-off product legs: Package I v0 composer route, Package N Macro writer/API + Terminal News rail, ticker-news secret mask heal"
    status: done
    pr: [8596, 8454, 8613, 8614, 8616]
    depends_on: [W6]
    next_action: "None for code. #8454 e3e3eff48cf4 (live, auth-gated, writer not armed), #8596 55e8cf84 (DEFAULT-OFF), #8613 643dcc3e, #8614 ca93b99f and Terminal #831 2cb3e164 (TICKER_NEWS_RAIL off) are MERGED. Activation moved to W8 under the Chairman's 2026-10-11 autonomy directive."
  - id: W8
    title: "Activation and VPS unit recovery under the Chairman's 2026-10-11 autonomy directive: Package N via Alpaca-sourced Benzinga headlines (#8809, then P2 VPS enable, P3 Terminal rail), Package I flag (#8811), market-memory unit recovery (#8807 massive manifest refresh, #8812 sentinel served cap, D-experience torn-pending discard, D-identity idempotent ingest, D-options pit EACCES tolerance + stage token), #7711 charter judgment"
    status: in_progress
    pr: [8809, 8811, 8807, 8812, 8816, 7711, 8820, 8823, 8818, 8819, 8826, 8828, 8829, 8830]
    depends_on: [W7]
    next_action: "Seat: #8828 SKYD-IDENTITY is MERGED 2026-10-11 as c50af4eb0421 (fold head 005c81ed737e; 8/8 blobs verified; the VPS pulled it; DSC:A-VENUE-MOVING-RENAME-MISSES-THE-COMMITTED-LISTING-KEY). P2 BLOCKED 17:04Z on HTTP 401 — the VPS holds the pre-rotation Alpaca pair (rotated 2026-08-04; DSC:VPS-ALPACA-CREDENTIALS-SILENTLY-REJECTED-SINCE-2026-08-04); remedy = #8838 .github/workflows/deploy-alpaca-secrets.yml (DEC:VPS-ALPACA-PAIR-REFRESHED-FROM-REPO-SECRETS-BY-DISPATCH-WORKFLOW), armed merge-on-green; after its merge the seat dispatches it from main (restart_press_feeds=false), then ORCH-N re-arms the writer (ticker-news-setup.sh --disarm/--arm), canary x2 >=10 min apart, then P3 (Terminal drop-in TICKER_NEWS_RAIL=1); the seat judges READY_FOR_SEAT_PROOF by artifact (is-active, two health reads, newsRailEnabled true at .deployment-id 707648d52014). DIDC #8830 (identity-intake checkout race; net-tree diff because /opt/macro is a depth-1 clone — DSC:DEPTH-ONE-DEPLOY-CLONE-DEFEATS-ANCESTRY-CHECKS) MERGED 17:26:55Z as 8a75b657d821 (--match-head-commit 3418a0e579bf; 2/2 blobs verified) and at PRODUCTION_PROOF: the 17:30:25Z identity-timer run saw HEAD move 8a75b657->b79cd122 mid-run, exited 0, completion_commit != deployed_commit (ORCH-OPS read 17:34:37Z, seat-judged). Open: the run used 165 s of TimeoutStartSec=180 (CPUQuota=50%) — lift the unit budget before the corpus times it out; the covering main proof is dispatched after run 38158841888 concludes and #8838 merges. #8823, #8818, #8819 MERGED (d39672a34aaa / 56e269cf2e3f / b8a839236ddd); #8819 PRODUCTION_PROOF. Live proofs still owed: #8807 technicals replay + #8816 W2C activation after the 10-12 nightly republishes the manifest. D-options: failure line PROVEN (fail-closed stage token at 15:00:23Z); capture is EXACT_HUMAN_GATE — Massive REST options snapshot 403 NOT_AUTHORIZED on the stock-plan key (plan entitlement = money), timer stays disarmed."
next_action: "W8 is running under two Opus orchestrators (ORCH-N Alpaca activation; ORCH-OPS I-flag + VPS unit recovery) over GLM fabric lanes; #8809/#8811/#8807/#8812/#8816/#7711/#8820/#8823/#8818/#8819/#8826/#8828/#8829/#8830 are MERGED (#8828 = c50af4eb0421, the SKYD fold), #8811/#8812/#8819 and the #8818 failure line are PRODUCTION_PROOF, and the main proof 38147853042 (186dbdce5aad) is SUCCESS; open: #8838 deploy-alpaca-secrets merge + dispatch from main (the VPS Alpaca pair is the pre-rotation copy, so P2 is blocked on 401 until it runs; DEC:VPS-ALPACA-PAIR-REFRESHED-FROM-REPO-SECRETS-BY-DISPATCH-WORKFLOW), then P2 canary -> P3 rail flip under ORCH-N (Package N production proof); #8830 PRODUCTION_PROOF (17:30Z moved-HEAD run exit 0) with the identity-unit timeout runway (165/180 s) to lift in a small unit-file PR; and the post-nightly live proofs (B, D-experience); program state is research/MARKET_INTELLIGENCE_BUILDOUT_CONTINUATION_HANDOFF_2026-10-11.md. Human-only after W8: Massive options-snapshot plan entitlement for the D-options capture (403 NOT_AUTHORIZED on the correct stock-plan key — money; DSC:MASSIVE-REST-OPTIONS-SNAPSHOT-NOT-ENTITLED-ON-STOCK-PLAN), F2-F5 (C19 reconciliation req-4a8daf76317cfe92f436991444c58281 + Executive OAuth), R (Research Vault custody under #8438), ITP GAP-E-BASIS/ALIAS (K3E owner), Package N body/image display (needs a direct Benzinga contract and a NEW receipt), the PSKY store-key migration (#4622 follow-on) and the KHC venue-transfer supersession (same wedge class, its owner's PR). The options-context auditor row boundary and the production-records MAX_SOURCE_ROWS bound both wait on an accepted preregistration v2 (Sol acceptance of the #7711 charter)."
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
  - "app/deploy/update.sh's macro-api restart regex is one long alternation line. Concurrent PRs always conflict on it (#8454 vs #8596, 2026-10-07). Heal with a keep-both union merge of origin/main plus `bash -n`."
  - "A new /etc/*.env secret must be masked (InaccessiblePaths=-) in every networked market-memory unit that lists secret masks. The deploy tests pin the full list only for options and technicals (#8613); #8614 masks it in the other 10 units."
  - "gate: data legacy jobs (e.g. market-memory-contract) run only in data-health.yml. A red there never blocks PR CI and is easy to blame on the newest merge."
  - "ORCH-OPS lanes pushed through the Git Data REST API or `git push --no-thin` because receive-pack answered HTTP 500 from ubuntu3/ubuntu2 (2026-10-11): a lane that reports 'pushed' is verified by ls-remote on the exact head, never by its own log."
  - "production-records is capacity-contract bound (29,509 source rows > MAX_SOURCE_ROWS 25,000, engine/neuralweb/market_memory_production_records.py:76): the ceiling belongs to WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2 / #7711 — never widen it from this program."
  - "/var/lib/macro-market-memory-options is root-owned 0710 by reviewed design (app/deploy/README.md:74-80): never chmod it; the option-OI fix is the narrow EACCES tolerance in market_memory_pit._ensure_store_directory_chain (DEC:MM-PIT-UNOWNED-PARENT-FSYNC-EACCES-IS-TOLERATED)."
  - "The identity store's refusal of a different digest for an already-captured date (engine/neuralweb/market_memory_identity_store.py:1537) is correct point-in-time behaviour: the fix is ingest idempotence plus a typed divergence receipt, never a store relaxation or a data/ rewrite (DEC:MM-IDENTITY-INGEST-IDEMPOTENT-OVER-CAPTURED-DATES)."
  - "Never start a market-memory production unit by hand on the VPS: live proof is the next SCHEDULED run's journald line; a hand start is invisible to every staleness instrument and contends for the shared update lock that app/deploy/update.sh and the setup scripts take."
  - "us_board_provisional staleness over a weekend is producer-side (the VPS mirror timer runs Mon..Fri 20..23:02/5:00 UTC with Persistent=false; the GitHub backstop published after the mirror's last tick): the next tick heals it; nothing to patch on the VPS."
  - "The Alpaca receipt caps every consumer of alpaca-rest rows at headline/teaser/source-link display; body_display and image_display are FALSE. A surface that renders body or image needs a NEW receipt with a basis that supports it, never an edit of config/ticker_news_rights_alpaca_benzinga.json."
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
  - "W6/W7 PRs #8567/#8583/#8587/#8588/#8454/#8596/#8613/#8614 and Terminal #831 are MERGED. Never re-open, rebuild a second composer, writer, API or rail, or re-register S2. Activation is a flag and a service enable, not code (DEC:MI-BUILDOUT-N-MERGES-INERT-ACTIVATION-IS-AN-OPERATOR-FLAG)."
  - "Alpaca rights basis is DECIDED (DEC:TICKER-NEWS-ALPACA-BENZINGA-RIGHTS-BASIS): do not re-ask whether the writer may ingest Benzinga-sourced headlines via Alpaca, do not buy a direct Benzinga feed for headline display, and never self-issue a receipt from API possession."
  - "D-identity option (a) and D-options fix (b) are DECIDED in the two DEC:MM-* records; repair rounds amend the lane packet, never the decision. The PIT correction class in the identity store is deferred OPEN under program market-memory, not this seat's to build."
  - "#7711 charter judgment is recorded ONCE (ten gaps F-G1..F-G10 in research/MARKET_INTELLIGENCE_BUILDOUT_CONTINUATION_HANDOFF_2026-10-11.md section 3); the GLM docs lane fixes them on the same branch and PR — never open a second charter, a second judgment lane, or a second preregistration."
  - "ORCH-OPS diagnoses D1-D6 (collector already-current path, daily.yml producer gap, update.sh timer cascade, production-records ceiling, sentinel BODY_CAP, us_board_provisional timer) are verified by artifact and recorded in the 2026-10-11 continuation file — do not re-diagnose."
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
  - research/MARKET_INTELLIGENCE_BUILDOUT_CONTINUATION_HANDOFF_2026-10-11.md
  - config/ticker_news_rights_alpaca_benzinga.json
  - collectors/alpaca_news.py
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
`research/MARKET_INTELLIGENCE_BUILDOUT_CONTINUATION_HANDOFF_2026-10-11.md` (W8; the 2026-10-06
file holds W1-W7). From W8 on, Opus 5.5 orchestrators (Chairman 2026-10-05/10-11) administer the
GLM fabric lanes for this program; they never spawn native children, never post, label, ready
or merge — those acts stay with the seat.
