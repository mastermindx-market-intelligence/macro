---
workstream: "WS:MARKET-OS"
session: policy-watch-official-events-r3-20260914-sol-001
model: sol
ended_because: blocked
mission: >
  Ship the next bounded Policy Watch capability after R1 and R2: a compact,
  source-backed official-policy-event discovery feed over the existing Europe
  event producer, while keeping publisher time, first-seen time, source-check
  time, lifecycle authority and market authority separate.
state_before: >
  Policy Watch R1 already supplied the Fed calendar, official headlines and
  statement history, and R2 added a dated analysis snapshot. The existing
  engine/europe_news_intel.py producer wrote point-in-time events and coverage
  to data/europe_news_vector and appended event identity through qbus, but no
  Policy Watch consumer exposed those records. The only user-facing fallback
  was the older curated World events cards.
changed:
  - path: engine/policy_watch_current.py
    what: >
      Adds a bounded, read-only official policy-event composer over the existing
      Europe events and coverage artifacts. It admits only rights-verified
      configured sources, exact publisher hosts, publisher-stated timestamps,
      existing event identities and focused policy themes; it prints typed
      current, partial, stale, outage, no-coverage and unavailable states and
      grants no rank, gate, sizing or trade authority.
  - path: scripts/build_policy_watch.py
    what: >
      Adds fail-closed bilingual display labels while preserving publisher date,
      first-seen collection instant and latest source-check instant as three
      different clocks.
  - path: templates/policy_watch.html.j2
    what: >
      Renders the feed inside the existing Policy stages section with source-
      original titles, bilingual publisher/theme/clock labels, direct official
      links, per-source health and an explicit discovery-only authority ceiling.
      The exact-head review repair makes partial copy cover delayed, stale,
      non-responding and not-yet-covered sources, and makes outage/stale saved-item
      copy conditional rather than promising rows that may not exist. The
      seven-section composition remains unchanged.
  - path: tests/test_policy_watch_ui.py
    what: >
      Adds RED-first producer/consumer regressions for rights, URL and identity
      admission, publisher and known-at clocks, per-source staleness, delayed and
      outage states, read-only behavior, bilingual copy and preservation of the
      R1, R2, UK and 44-call surfaces. Three additional RED-first render tests pin
      truthful partial, empty-outage and empty-stale explanations after exact-head
      review found the prior copy overclaimed degraded conditions.
  - path: docs/plans/2026-09-14-policy-watch-official-events-r3.md
    what: >
      Freezes the bounded owner, time/null/correction, UI and production-proof
      contract for this vertical.
  - path: mockups/evidence/policy-watch-event-r3/
    what: >
      Records the exact semantic code commit, real-input render receipt, source
      view, eight-cell dark/light EN/ZH desktop/mobile matrix, DOM assertions and
      UX-smell census. Local evidence is source-ready proof, not public proof.
  - path: agentos/handoffs/MARKET-OS-2026-09-14-policy-watch-official-events-r3.md
    what: >
      Records the capability delta, exact evidence, remaining hosted/public gates
      and no-rebuild laws for a cold-start continuation.
prs: [7136]
verified:
  - claim: >
      Current protected Sol procedure was loaded atomically before the modifying
      continuation.
    command: >
      GitHub reads of docs/sol_skills/INDEX.md, COLD_START.md,
      RECONCILE_STATE.md, REVIEW_RETURN.md and CLOSEOUT.md at Mastermind protected
      master 6061c0b32f1adad56a1282bbc01e70ce7f0a5a44.
    result: >
      Every file declares mastermind.sol_skillpack.v1, Skillpack 1.0.1 and
      minimum bootstrap major 1; compatible with bootstrap major 1.
  - claim: >
      The real bounded Policy Watch, lifecycle, UK, macro-news and Europe producer
      surfaces remain green with the R3 consumer.
    command: >
      MM_DATA_GUARD=trace PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q
      -p no:cacheprovider --basetemp=/tmp/pw-r3-full-repair-final
      tests/test_policy_calendar.py tests/test_policy_dates.py
      tests/test_policy_intent_desk.py tests/test_policy_layer_leaves.py
      tests/test_policy_lever.py tests/test_policy_lifecycle.py
      tests/test_policy_summary.py tests/test_policy_watch_register.py
      tests/test_policy_watch_ui.py tests/test_uk_policy_brain.py
      tests/test_macro_news.py tests/test_europe_news_intel.py
    result: "345 passed in 88.18 seconds on Python 3.12.13."
  - claim: >
      R3-specific truth, time, rights, degraded-state and UI regressions are green.
    command: >
      MM_DATA_GUARD=trace PYTHONDONTWRITEBYTECODE=1 python3 -m pytest
      tests/test_policy_watch_ui.py -q -p no:cacheprovider
      --basetemp=/tmp/pw-r3-repair-r3-all -k 'r3_'
    result: "21 passed, 109 deselected in 5.94 seconds; the three repair regressions were first observed RED with the expected copy assertions."
  - claim: >
      Semantic implementation bytes are pinned independently of the evidence
      commit.
    command: >
      git show --stat --oneline 8b94d19648ab74ee99fb4e5c6e97c97eb855ae8a
      and read mockups/evidence/policy-watch-event-r3/render-receipt.json.
    result: >
      Repaired semantic code commit 8b94d19648ab74ee99fb4e5c6e97c97eb855ae8a,
      tree 32229dac08a0ff59e768e5ee2692af6556d0527c; the receipt carries
      SHA-256 for every source path and rendered page 24700f5ae337816f9f7e197d1e7c39223b4bd27981a49314f931d780c694c2e7.
  - claim: >
      Current checked-in Europe artifacts produce a useful real feed without
      widening authority.
    command: >
      build_policy_event_feed(Path.cwd()) followed by the real
      scripts.build_policy_watch builder and externalize_css; receipt at
      mockups/evidence/policy-watch-event-r3/render-receipt.json.
    result: >
      State current and fresh; Bank of England and European Commission both
      COVERED; four admitted official events; one feed; seven top-level sections;
      current Fed panel, UK desk and all 44 calls preserved; can_rank, can_gate,
      can_size and can_trade remain false; rendered page SHA is receipt-bound.
  - claim: >
      Production-shaped browser behavior holds in every required visual cell.
    command: >
      python3 scripts/capture_page_evidence.py for policy_watch.html across
      desktop/mobile, EN/ZH and light/dark, followed by
      python3 /tmp/policy_watch_r3_dom_probe_repair.py.
    result: >
      Eight of eight cells captured and accepted on repaired semantic commit
      8b94d19648ab; HTTP 200; four real events; correct localized publisher and
      clock copy; one current-state explanation; R2 clock, current panel, UK desk,
      44 calls and seven sections preserved; zero console errors, page errors,
      failed requests, visible machine tokens or horizontal overflow. Degraded
      state wording is separately bound by the RED-first render regressions and
      template source receipt rather than falsely claimed visible in a current-state page.
  - claim: >
      Source and repository contracts are clean before hosted CI.
    command: >
      git diff --check; py_compile; Ruff E9,F63,F7,F82;
      check_design_system --mode enforce-added; check_runtime_style_injection;
      check_zh_filing_term; check_ui_visual_evidence; check_template_site_sync;
      check_contract_delta --base origin/main; audit_unrun_tests; agentos validate.
    result: >
      Diff and compile clean; Ruff clean; zero added design findings; runtime
      style guard green; no unlicensed filing term; visual-evidence gate green
      over eight refreshed screenshots; 98 template/site pairs in sync; contract
      delta 0 introduced and 0 inherited against base a0515d73b9fe; unrun audit
      exits 0 over 2,774 suites with zero strictly-dark suites and only inherited
      warnings; Agent OS reports 0 errors and 49 inherited warnings.
  - claim: >
      Current main movement is compatible and does not collide with this carrier.
    command: >
      git fetch origin main; git diff --name-status HEAD..origin/main;
      git merge-tree --write-tree HEAD origin/main; owned-path intersection.
    result: >
      Main movement is generated data and site publication only; zero owned-path
      collisions; merge-tree succeeds without conflicts. Main ancestry alone is
      not treated as a reason to rebuild or force-merge generated movement.
  - claim: >
      The predecessor R2 analysis-snapshot capability is merged and proven on the
      canonical public route before R3 release.
    command: >
      Read PR7109 merge identity; compare SHA-256 of current main, production
      checkout, site.served and the public CDN response; run the canonical page
      evidence harness against https://www.mastermind-x.com/policy_watch.html.
    result: >
      PR7109 merged as 08d437b1c6d9a45ae5bab4111240e71418b3b10c;
      all four served/source byte surfaces matched SHA-256
      1eddf3a56c6adb3aeb9eb4f0564f85760eba7bdcdee6064fb60e7a514449cccf;
      eight of eight public desktop/mobile, EN/ZH, dark/light states captured with
      zero console errors, failed responses or horizontal overflow. R2 is
      PROVEN_LIVE and is a preserved dependency, not work R3 may rebuild.
unverified:
  - claim: "Independent exact-head adversarial review accepts the complete final PR head."
    what_would_verify: >
      A non-builder Opus reviewer returns PASS on the exact final head after
      inspecting code, tests, receipts and screenshots.
  - claim: "Hosted exact-head CI and merge-ref proof conclude green."
    what_would_verify: >
      Push the evidence/handoff commit, observe every binding GitHub check to a
      terminal conclusion, and merge only the expected head.
  - claim: "The canonical public Policy Watch route serves the R3 feed."
    what_would_verify: >
      After normal render publication, repeat the eight-cell DOM/browser proof on
      https://www.mastermind-x.com/policy_watch.html and bind the served page to
      merged main.
unresolved:
  - >
    Current Europe coverage is intentionally narrow: only public-reuse European
    Commission and Bank of England sources are admitted. Rights-excluded ECB,
    Council and Eur-Lex rows remain printed nulls in the producer and cannot enter
    the consumer without their existing rights/source gates being resolved.
  - >
    R3 is discovery context only. It does not classify an event into a deterministic
    policy lifecycle stage, produce affected-asset relationships, or earn signal,
    rank, gating, sizing or trade authority.
  - >
    Public production acceptance remains owed after exact-head review, CI, merge
    and normal publication.
next_actions:
  - >
    Obtain independent exact-final-head Opus review; repair every blocker or major
    finding with a regression and re-review until PASS.
  - >
    Run final-head local gates, push, make PR7136 Ready, arm normal merge-on-green,
    wait for all binding checks to conclude and squash-merge only the expected head.
  - >
    Follow the normal render publication and run canonical public eight-cell proof;
    only then write the PROVEN_LIVE closeout and supersede this blocked handoff.
do_not_redo:
  - >
    Do not create another policy event database, collector, scheduler, queue,
    identity key, correction ledger or coverage store; use europe_news_intel and
    qbus.
  - >
    Do not infer or advance policy lifecycle state from a news/event title; the
    deterministic lifecycle owners remain policy_intent_desk and
    transmission_chains.
  - >
    Do not translate source-original titles and pretend the translation is the
    publisher's wording; Chinese mode labels them 原文标题.
  - >
    Do not use build time, file mtime, review-by dates or UTC date conversion as a
    substitute for publisher date, first-seen time or source-check time.
  - >
    Do not reopen or replace the R1 Fed composer, R2 analysis clock, UK desk,
    seven-section page composition or 44-call ledger.
  - >
    Do not promote the display feed to score, rank, gate, size or trade authority
    without a separately validated and explicitly accepted promotion program.
danger_areas:
  - >
    One fresh source must not hide another stale source. Per-source health is
    calculated before aggregate state; delayed-only coverage is partial but not
    fresh.
  - >
    Publisher calendar date and UTC instant are different facts. The visible date
    preserves the publisher's own offset date while the full instant is normalized
    to UTC.
  - >
    Rights-excluded rows can exist in coverage.parquet but must not affect displayed
    health, source chips or item admission.
  - >
    A source outage may retain saved dated context, but the view must remain not
    fresh and must not imply a successful current acquisition.
  - >
    Local screenshots and DOM proof demonstrate source-ready bytes, not canonical
    public adoption. Merge, render publication and live proof are separate gates.
---

## §0 State — what is true right now

PR #7136 contains a source-ready official-policy-event consumer built on the existing Europe
producer and qbus identity plane. Exact-head review found one material truth-copy defect on the
worker return; the RED-first repair is semantic commit
`8b94d19648ab74ee99fb4e5c6e97c97eb855ae8a`. Real checked-in inputs produce four current official
events, all 345 bounded tests pass, and the refreshed local eight-cell browser contract passes. The
capability remains **BUILT_NOT_PROVEN** because exact-final-head independent review, hosted CI,
merge, normal publication and canonical public proof are still separate unfinished gates.

## §1 What is LEFT — in order

1. Review the exact final PR head independently with Opus against the frozen owner, rights, clock,
   null, authority and browser-evidence contract. Repair blocker/major findings and repeat until PASS.
2. Re-run all final-head tests and guards, push the exact reviewed head, mark PR #7136 Ready and arm
   the normal merge-on-green path.
3. Wait for every binding check to conclude. Merge only the expected head; a queued/running check is
   not a pass and generated main movement is not a source collision by itself.
4. Follow the normal render owner. On the canonical public URL, repeat the eight-cell DOM/browser
   proof and compare the served page with merged main before recording PROVEN_LIVE.

## §2 What will bite you

The three clocks are easy to collapse accidentally. Publisher date preserves the publisher's own
calendar day; `known_at` is the first-seen instant; `coverage_checked_at` is the source-health clock.
A UTC conversion can move the calendar date and create a false publication label. Source health is
also per source: using only the newest aggregate check lets one fresh source hide another stale one.
Finally, `coverage.parquet` intentionally contains rights-excluded rows; treating every row as a
health input silently grants rights-excluded sources authority they do not have.

## §3 What was decided and found

No new DEC or DSC record was necessary. This wave applies the existing F02 owner/source/rights map,
qbus single-event-system law and Policy Watch R1/R2 no-rebuild boundaries. The durable new fact is
fully captured in this handoff and PR #7136: the existing Europe producer had a useful but dark real
consumer gap, and the bounded Policy Watch projection now closes it without changing authority.

## §4 Not in scope — do not adopt

This wave does not expand source rights, add geopolitical/military/maritime/satellite coverage,
create policy-to-asset causal edges, translate publisher titles, change the lifecycle state machine,
modify predictions or historical calls, or create any forecast/trade authority. Those are separate
programs and gates; absorbing them here would turn one useful vertical into another strategic rebuild.
