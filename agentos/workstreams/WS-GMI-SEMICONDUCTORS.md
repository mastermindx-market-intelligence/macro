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
      LANDING ORDER (binding, from #7870 comment 6105402719 line 18): Industrials #8250
      (adjudicated 6105257496, repaired 6105272573, RED at 20e7e9ac on the curated-closure
      contract, repaired again at 1db9cad104437dc0c9bb4b27cf45781040302fb2 = merge of
      origin/main f191b7f1 plus a two-line path widening) lands on main FIRST;
      #7870 then merges main (the comment's "rebases afterward" is implemented as a merge of
      main into the branch with no history rewrite; its resolution is read against each parent)
      and resolves its collision set with #8250, which the pairwise comparison of #7870's 102
      fully paginated changed paths against #8250's changed paths (NOT the adapter's census)
      fixes at exactly two paths: engine/company_intelligence/issuer_profiles.py, where the
      2026-10-11 dry run `git merge-tree --write-tree acc72f3f 20e7e9ac` in the #7870 worktree
      produced tree 8a957225cc5ca8c3cd589552b336882c38c826af with "CONFLICT (content)" and
      `git show <tree>:engine/company_intelligence/issuer_profiles.py | grep -c '^<<<<<<<'`
      printed 3; and .github/ci/legacy-jobs.yml, auto-merged with 0 markers.
      Green and the delta review at acc72f3f are evidence for the pre-merge tree only.
      Gate set per DEC:FABLE-SEAT-IS-CEO-COEQUAL-WITH-SOL, stated completely: (1) semantic pass:
      the H1 ruling B (#7870 comment 6105015260) plus the consumed independent Opus audit of
      b76551be (DEC:SEMICONDUCTOR-B-H1-FINANCE-ADAPTER-HOLDS-SECTOR-PROFILE); (2) fresh non-author
      exact-head review: IN HAND for b76551be..acc72f3f as #7870 comment 6105402719 (independent
      READ_ONLY Opus, VERDICT ACCEPT_DELTA, 2026-10-11; two LOW and three INFO findings, none
      blocking; the LOW on a literal test path inside an engine comment is closed by hosted
      contract-delta and fence-pack success at acc72f3f), PLUS one further non-author READ_ONLY
      read of the merge resolution at the post-#8250 head (the merge commit diffed against each
      parent, not the base-inclusive range acc72f3f..<new head>), still owed; (3) hosted checks:
      ALL_CONCLUDED green from exactly one watcher bound to the exact post-merge release head,
      still owed (the merge-queue pilot is not a gate); (4) Source Continuity, NOT self-ruled: the
      official read-only verifier was run on 2026-10-11 at acc72f3f from the Mastermind main
      checkout at c7e47c859eb2925c5626931fd511800773ba09ac (scripts/source_continuity.py last
      changed at 6eb1989d, 2026-09-25, "fix(source-continuity): scale Macro census to 490
      (#982)"; _MAX_COLLISION_PRS = 490 at :77, refusal branch at :1337) with verify --kind
      remote-complete, operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001, PR
      7870, base main pinned at 363b4e6296b7598ad8980b6a1b8b9444e14cfd6b, the 102 changed paths
      as owned paths, external effect NONE / dependency NONE, and exited 2 with the typed
      refusal {"code":"REMOTE_CENSUS_INCOMPLETE","message":"remote proof census is
      incomplete","ok":false,"schema":"mastermind.source_continuity_refusal/v1"}. Cause: the
      repository had 632 open PRs against the cap of 490 (gh api graphql -f query='{repository(
      owner:"mastermindx-market-intelligence",name:"macro"){pullRequests(states:OPEN){totalCount
      }}}' -> {"data":{"repository":{"pullRequests":{"totalCount":632}}}} at
      2026-10-11T05:12:45Z). The cap sits inside a protected resource envelope (Mastermind
      docs/superpowers/plans/2026-09-24-source-continuity-macro-490-scale.md, canonical owner
      Mastermind issue #346: 1,152 logical HTTP calls, 128 MiB, 300 s, 5,000,000-byte
      responses; tests pin (490, 1152); "491+ remains outside this successor and must fail
      closed"), so raising it is a protected-source change owned by the #346 series, not a
      constant this seat may tweak; no REMOTE_COMPLETE_VERIFIED receipt is obtainable for any
      Macro carrier until that series lands or open PRs fall to 490 or fewer. The protocol
      text (COMMISSION_WAVE.md:303-306, REVIEW_RETURN.md:205-211) describes the STARTed-child
      case and is silent on heads with no child; the seat infers no exemption from that
      silence. Whether any STARTed child or writer lease exists on #7870 is unverified from
      this seat (Executive OS unreachable); nothing below is conditioned on that premise.
      Precedent followed, not distinguished: DEC:FABLE-SEAT lines 38 and 41 (Sol blocked
      Mastermind #716 on the missing receipt alone; the seat's own repair head 7dbb4230
      carried REMOTE_COMPLETE_VERIFIED). Binding form: the verifier is re-run at the
      post-merge release head from the pinned Mastermind revision with a real
      evidence-artifact fingerprint (sha256 of the recorded census JSON, not of an assertion)
      and its JSON is quoted verbatim in the DECISION; REMOTE_COMPLETE_VERIFIED puts gate (4)
      in hand; ANY refusal means RELEASE_BLOCKED unless a non-seat authority (the Chairman or
      Sol) accepts the recorded substitute on #7870 by a cited comment or message id before
      the DECISION. The seat requested that ruling on #7870 (comment 6106057199, 2026-10-11) and
      does not rule on it. Substitute evidence recorded with commands on 2026-10-11 and
      offered for that ruling: git ls-remote origin refs/heads/<branch> == git rev-parse HEAD
      == acc72f3f; the GitHub commit tree cd76b979136ccd77bc4bfd50b14c9f5fa19d4a93 == git
      rev-parse HEAD^{tree}; gh api pulls/7870/files fully paginated (102 paths) == git diff
      --name-only 363b4e62..acc72f3f; the pairwise collision set with #8250 = the two paths
      above; and the extended open-PR collision census of 2026-10-11 (632 open PRs enumerated at 2026-10-11T05:12Z (634 at 05:59Z; the two newer PRs are not censused), 0 enumeration failures, 190 PRs touch at least one of #7870's 102 owned paths, 139 of them only via .github/ci/legacy-jobs.yml, all 190 diverged from acc72f3f, none stacked; issuer_profiles.py shared only with #8250; census JSON sha256 f51180b7b6e6915ef5e07de6aca663fbf98374a5e94ba05c40e874f3f1ff770c). With
      (1)-(4) in hand at the post-merge head: a fresh
      carrier read before EVERY post and act (DEC:FABLE-SEAT line 60), then ONE release
      DECISION in DEC:FABLE-SEAT order (quote the Chairman ruling, cite the consumed audit, the
      delta review and the merge-resolution read, ACCEPTED/STOP, BRANCH_WRITER_RELEASED, review
      state, body, Ready, merge queue), each act asserting the exact head. On red: repair in
      scope, new head, re-bind the watcher, extend the non-author review to the repair delta.
      On HEAD_CHANGED: re-read before anything.
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
  The b76551be..acc72f3f delta review is in hand (#7870 comment 6105402719); #8250 lands
  first, then the non-author read of the merge resolution, green at the post-merge head and
  gate (4) (a binding Source Continuity re-run returning REMOTE_COMPLETE_VERIFIED, or a
  non-seat acceptance of the recorded substitute on #7870 by cited id; a refusal without
  that acceptance is RELEASE_BLOCKED) are owed before any release act. After release, open SB-W2 (Option A) first because
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
