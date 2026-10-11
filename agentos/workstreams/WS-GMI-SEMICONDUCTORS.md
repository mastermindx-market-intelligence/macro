---
key: GMI-SEMICONDUCTORS
title: Semiconductor Theme Intelligence B — shared theme-research foundation and the Semiconductor vertical
objective: >
  Land the shared theme-research foundation carried by #7870 (the VerticalRegistration
  shell, curation assertion, owner-bundle wire grammar, shared routes) at its approved
  scope so every other vertical integrates into ONE base instead of rebuilding it; then
  build the Semiconductor vertical content on that base. Done = #7870 merged at approved
  scope with the separable-foundation evidence accepted, the Option A registry follow-on
  landed, and the Semiconductor vertical served with rights-qualified evidence.
status: active
program: gmi-theme-graph
repos: [macro]
owner: fable-meta-ceo
class: build
blast_radius: user_facing
ambiguity: scoped
depends_on:
  - WS:GMI-THEME-GRAPH
owns_paths:
  - engine/market_ontology/theme_research_registry.py
  - engine/sector_intelligence/finance_research_registration.py
  - tests/test_theme_research_registry.py
  - tests/test_finance_research_registration.py
decisions:
  - DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11
  - DEC:SEMICONDUCTOR-B-H1-FINANCE-ADAPTER-HOLDS-SECTOR-PROFILE
  - DEC:FABLE-SEAT-IS-CEO-COEQUAL-WITH-SOL
landmines:
  - "engine/theme_graph/store.py is frozen by #7462 and templates/basket_detail.html.j2 by #7669: never edit either on this carrier."
  - "Macro is PUBLIC: no paid research payloads, credentials or private screenshots in any commit; no new private store."
  - "tests/test_research_priority_ordering.py is RED on origin/main (30 TemplateNotFound: _finance_sector_deep_dive.html.j2 missing from _SUPPORT_PARTIALS) and is not this carrier's defect; it is packet P-FIN-1."
  - "An xfail with raises=ValueError absorbs every refusal that subclasses ValueError; a hold that must discriminate causes needs an exact-string assertion (DEC:SEMICONDUCTOR-B-H1-FINANCE-ADAPTER-HOLDS-SECTOR-PROFILE)."
  - "Never bare git stash in the shared store; never mutate git in the main checkout; the worktree lives on the external SSD."
do_not_redo:
  - "H1 is ruled (B) and implemented at acc72f3f; do not re-open the registry identity grammar on #7870. Option A is a separate carrier."
  - "C1 (SBD-41..48) is DEFERRED by ruling; V1.1 (object.subject_role optional) is PROPOSED_NOT_BUILT; rights qualification is QUEUED_NOT_STARTED and blocked on the Robotics R1 corpus."
  - "The merge-queue pilot is NOT a gate for this carrier (two pilots merged red)."
waves:
  - id: SB-W1
    title: "Shared foundation carrier #7870 at approved scope: H1 ruled B, b76551be audit and acc72f3f delta review consumed, hosted checks owed"
    status: awaiting_ci
    pr: 7870
    next_action: >
      Head acc72f3fb3efb1ad092359ce2ba4190de66d75e1 is pushed with the H1-B audit repairs.
      A session-local CI watcher was bound to that exact head on 2026-10-11; a successor
      verifies it is live (control_plane owns liveness) and otherwise binds exactly one.
      Gate set per DEC:FABLE-SEAT-IS-CEO-COEQUAL-WITH-SOL, stated completely: (1) semantic pass:
      the H1 ruling B (#7870 comment 6105015260) plus the consumed independent Opus audit of
      b76551be (DEC:SEMICONDUCTOR-B-H1-FINANCE-ADAPTER-HOLDS-SECTOR-PROFILE); (2) fresh non-author
      exact-head review: IN HAND for b76551be..acc72f3f as #7870 comment 6105402719 (independent
      READ_ONLY Opus, VERDICT ACCEPT_DELTA, 2026-10-11; two LOW and three INFO findings, none
      blocking; the LOW on a literal test path inside an engine comment is closed by hosted
      contract-delta and fence-pack success at acc72f3f); (3) hosted checks: ALL_CONCLUDED green at
      the exact release head, still owed; (4) the canonical Source Continuity receipt
      (CHECKPOINT_VERIFIED / REMOTE_COMPLETE_VERIFIED) is named by the protocol for a STARTed
      source-modifying fabric child; acc72f3f was built and pushed by this seat directly with the
      fabric unavailable, so no STARTed child exists to carry one, and the release DECISION's
      exact-head assertions (worktree rev-parse equals the gh head, clean tree, merge-tree against
      the pinned base sha) are the source-identity evidence instead. The review in (2) is pinned to
      acc72f3f: if the release head moves (a red repair, or the rebase onto main after Industrials
      #8250 lands first on the shared issuer_profiles.py seam, per comment 6105402719), extend the
      non-author review to acc72f3f..<new head> before release and re-bind the hosted gate to the
      new head. With (1)-(4) in hand: fresh carrier read, then ONE release DECISION in
      DEC:FABLE-SEAT order (quote the Chairman ruling, cite the consumed audit and the delta
      review, ACCEPTED/STOP, BRANCH_WRITER_RELEASED, review state, body, Ready, merge queue), each
      act asserting the exact head. On red: repair in scope, new head, re-bind the watcher, extend
      the review. On HEAD_CHANGED: re-read before anything.
  - id: SB-W2
    title: "Option A registry follow-on: entry_kind admitting sector_profile/company_profile, optional anchor"
    status: todo
    depends_on: [SB-W1]
    next_action: >
      Open a separate carrier after #7870 lands. Consumers waiting on it: Finance
      (sector_profile hold), Technology #7891 (company_profile, anchor None), Consumer
      Cyclical #7780 (R15 H2 grammar).
  - id: SB-W3
    title: "Semiconductor vertical content: rights qualification, V1.1 subject_role, deferred C1"
    status: todo
    depends_on: [SB-W1]
    next_action: >
      Rights qualification stays QUEUED_NOT_STARTED until the Robotics R1 corpus exists;
      C1 stays DEFERRED until re-commissioned. Do not start either on a hunch.
next_action: >
  2026-10-11: the seat consolidated under DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11.
  SB-W1 is the critical path for every vertical below it. Consume the verdict of the one
  live CI watcher at acc72f3f (bind exactly one if none is verifiably live); do not poll it.
  Obtain the owed non-author delta review before any release act. After release, open SB-W2 (Option A) first because
  three verticals block on it, then re-land Robotics (WS:GMI-ROBOTICS) and reconcile
  Energy #8002 (WS:GMI-ENERGY-NUCLEAR) onto the accepted base.
---

## Carrier and custody

- Operation `gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001`.
- Carrier PR #7870, branch `claude/ssd-semiconductor-theme-intelligence-b-impl-988406e131fd90b9`,
  head `acc72f3fb3efb1ad092359ce2ba4190de66d75e1` at the time of this record.
- Truthful state lines: MISSION_COMPLETE FALSE; SEMICONDUCTOR_B NOT_BUILT; C1 DEFERRED;
  V1_1 PROPOSED_NOT_BUILT; RIGHTS_QUALIFICATION QUEUED_NOT_STARTED; H1 RULED_B_IMPLEMENTED_AT_acc72f3f;
  DELTA_REVIEW ACCEPTED_AT_acc72f3f (#7870 comment 6105402719); FABRIC UNAVAILABLE; READY/MERGE NOT_YET.
- Builder is not reviewer: the H1-B change was audited by an independent read-only
  Opus auditor at b76551be before the repairs were applied, and the repairs themselves
  (b76551be..acc72f3f) received a second independent read-only Opus review (#7870 comment
  6105402719, ACCEPT_DELTA); any further head move owes the same review for its own delta.
