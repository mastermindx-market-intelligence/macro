---
workstream: "WS:GMI-SEMICONDUCTORS"
session: "claude/ssd-semiconductor-theme-intelligence-b-impl-988406e131fd90b9 (Fable 5.1 Meta-CEO seat; records worktree industry-intelligence-agentos-records-8ac42406fdf3c425)"
model: fable
ended_because: ci_handoff
prs: [7870]
decisions:
  - "DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11"
  - "DEC:SEMICONDUCTOR-B-H1-FINANCE-ADAPTER-HOLDS-SECTOR-PROFILE"
mission: >
  Chairman directive 2026-10-11: consolidate every industry intelligence vertical under one
  owner, run that owner as the Fable 5.1 Meta-CEO with Opus 5.5 suborchestrators that fan out
  to the Executive/Subagent Fabric. Standing lane inside that: continue #7870 as the single
  shared-source owner, close the remaining shared executable defect (H1), and release the
  carrier at its approved separable scope once the gates are in hand.
state_before: >
  Eleven industry workstreams were split across coo-fable, ceo-fable, ceo-sol, chairman and
  fable-integration-principal owners, with no Agent OS record for Semiconductors, Technology
  ex-Semis, Energy/Nuclear, Robotics or Communications at all; their only durable state was
  PR comments and the Theme-Graph record's wave list. #7870 sat at b76551be with H1 ruled B and
  implemented, an Opus audit returned ACCEPT_WITH_FIXES, and the fixes had not yet landed.
  Robotics was still believed to be on main; it is not (#7908 merged 2026-09-25T07:27Z, then
  #8013 reverted it the same day at e5512ef66a74 because 11 first-party imports were unresolved).
changed:
  - path: engine/sector_intelligence/finance_research_registration.py
    what: >
      Macro PR 7870, head acc72f3fb3efb1ad092359ce2ba4190de66d75e1. H1 ruling B: the adapter
      raises FinanceRegistrationRefusal("vertical_registration_held:sector_profile") BEFORE
      constructing VerticalRegistration whenever the facts lack a string anchor_theme_id or a
      non-empty slice_keys. No anchor is invented, no sector_profile is fabricated; the 12-of-14
      field gap is pinned as a typed hold rather than absorbed by an xfail marker.
  - path: tests/test_finance_research_registration.py
    what: >
      Macro PR 7870, same head. The absorbing xfail(raises=ValueError) on the shared-shell
      round trip is DELETED and replaced by an exact-string assertion on the hold code plus a
      positive control that proves the hold fires on the real adapter, not on a fake. The audit
      fixes from the Opus ACCEPT_WITH_FIXES are folded in at acc72f3f.
  - path: agentos/decisions/DEC-CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11.md
    what: >
      New. Records the Chairman's verbatim consolidation and Meta-CEO directive, the three
      fences (Astra Theme-Graph lane observe-only, Sol writers on #7976 and #8678 untouched,
      STSI #8404 keeps its Astra pickup), and the owner transfers to fable-meta-ceo.
  - path: agentos/decisions/DEC-SEMICONDUCTOR-B-H1-FINANCE-ADAPTER-HOLDS-SECTOR-PROFILE.md
    what: >
      New. Records ruling B for H1, why the absorbing xfail had to be deleted rather than
      satisfied, and what the Option A registry entry_kind carrier (SB-W2) must carry.
  - path: agentos/workstreams/WS-GMI-SEMICONDUCTORS.md
    what: >
      New. SB-W1 awaiting_ci on #7870 (the nearest enum value; it waits on #8250 landing, the merge-resolution read, green and the Source Continuity gate, not on CI alone) with the release-DECISION procedure in next_action,
      SB-W2 (Option A) and SB-W3 (rights / V1.1 / C1) todo, truthful state lines in the body.
  - path: agentos/workstreams/WS-GMI-TECHNOLOGY-EX-SEMIS.md
    what: New. TEC-W1 in_progress on #7891 with an external_dependency wait on #7870 and SB-W2.
  - path: agentos/workstreams/WS-GMI-ENERGY-NUCLEAR.md
    what: >
      New. ENE-W1 in_progress on #8002 (stacked on #7870 commit 6cd958e9 through its base
      branch claude/energy-stack-base-b-6cd958e9; never merged or retargeted before #7870 is
      released, then retargeted to main) with the 12-to-14
      VerticalRegistration arity landmine at tests/test_nuclear_research_route.py line 27.
  - path: agentos/workstreams/WS-GMI-ROBOTICS.md
    what: New. ROB-W1 done as the merge-then-revert pair [7908, 8013]; ROB-W2 re-land todo.
  - path: agentos/workstreams/WS-GMI-COMMUNICATIONS.md
    what: New. COM-W1 in_progress on #8039 (claude/communications-a1-measures-20260924) with wait.
  - path: agentos/workstreams/WS-GMI-FINANCE-INTELLIGENCE.md
    what: >
      Owner coo-fable -> fable-meta-ceo; depends_on WS:GMI-SEMICONDUCTORS; links the two new
      DECs plus DEC:FINANCE-SEC-EVIDENCE-RIGHTS-HELD-UNTIL-FAMILY-ADMITTED; the "round trip is a
      strict xfail until §8 is adjudicated" sentence is replaced because that state no longer
      exists; dated consolidation note naming the P-FIN-1 packet.
  - path: agentos/workstreams/WS-GMI-HEALTHCARE.md
    what: Owner -> fable-meta-ceo; DEC link; dated note making D1 live-proof VERIFICATION the first act.
  - path: agentos/workstreams/WS-GMI-INDUSTRIALS-FIRST-VERTICAL.md
    what: DEC link; dated note that T02 carrier #8250 was adjudicated at 20b853e2907e (#8250 comment 6105257496, REPAIR_REQUIRED), repaired at 20e7e9ac63759099704a46506e85b61d00b487fc (comment 6105272573); hosted checks at 20e7e9ac went RED (run 38110427910: contract-delta, ci-pack-0, ci-gate) on a NEW curated-closure contract defect that lives only on origin/main (nw-lobe-unfreeze and ticker-news-qbus are scope: exclusive there and declare issuer_profiles.py, whose lazy import of industrials_profiles.py left the closure uncovered); repaired by merging origin/main f191b7f1 into the carrier (03d29dfea9d8) plus a two-line path widening (1db9cad104437dc0c9bb4b27cf45781040302fb2, pushed 2026-10-11, local closure check {} ); it lands first on the #7870 release path once the four conditions in next_actions[0] below are in hand (green at 1db9cad1; the non-author review chain 20b853e2..20e7e9ac per 6105272573 and 20e7e9ac..1db9cad1 per 6106321419; gate (4) applied to #8250 in its own terms, its own substitute recorded in #8250 comment 6106395498; the custody reconciliation); status at the pushed head of this records PR is green and review chain in hand, gate (4) and custody owed.
  - path: agentos/workstreams/WS-GMI-MINING-M1-INTEGRATION.md
    what: DEC link; dated note that the T02 gate is OPEN because #7905 merged 2026-09-30 as cdce3023fbba, verified by the fiscal_scope presence check on main a4d48836a69e (4 hits).
  - path: agentos/workstreams/WS-CONSUMER-DEFENSIVE-CDV1.md
    what: DEC link; dated note that #8245 @b019f975c695 already carries the independent REQUEST_CHANGES issue comment 5927055846 at that exact head, so the next act is the P2 scoped-reader fix (CDV-T4); the repaired head then needs a fresh non-author exact-head review before any ruling; T7/T8 still wait on #7870.
  - path: agentos/workstreams/WS-CONSUMER-CYCLICAL-V1.md
    what: Owner -> fable-meta-ceo; both DEC links; dated note that #7870 is the critical-path blocker.
verified:
  - claim: "#7870 local head equals acc72f3fb3efb1ad092359ce2ba4190de66d75e1 and the PR head read by gh agrees."
    command: "git -C <7870 worktree> rev-parse HEAD; gh pr view 7870 -R mastermindx-market-intelligence/macro --json headRefOid -q .headRefOid"
    result: "both print acc72f3fb3efb1ad092359ce2ba4190de66d75e1; worktree clean"
  - claim: "At acc72f3f the Finance registration suite is green locally with the shell present, and the hold fires on the real adapter."
    command: "/opt/homebrew/bin/python3 -m pytest tests/test_finance_research_registration.py -q"
    result: "100 passed, 1 warning; the positive-control test observes vertical_registration_held:sector_profile from the unpatched adapter"
  - claim: "No tests/test_sector_intelligence_shared_shell.py exists at acc72f3f; the earlier three-count claim named a file that is not in the tree."
    command: "ls tests | grep -i shared_shell"
    result: "(empty output: no file name matched)"
  - claim: "At acc72f3f the theme research registry suite is green locally."
    command: "/opt/homebrew/bin/python3 -m pytest tests/test_theme_research_registry.py -q"
    result: "64 passed, 1 warning"
  - claim: "The Agent OS validator stays at zero errors with the 7 new records and 6 edited records."
    command: "/opt/homebrew/bin/python3 scripts/agentos.py validate"
    result: "literal output of the run at the pushed head: agentos: 1610 records (88 workstreams, 428 decisions, 478 discoveries, 616 handoffs) — 0 error(s), 145 warning(s)"
  - claim: "Robotics is NOT on main: #7908 merged and #8013 reverted it."
    command: "gh pr view 7908 -R mastermindx-market-intelligence/macro --json state,mergedAt,mergeCommit; gh pr view 8013 ... --json state,mergedAt,mergeCommit,title"
    result: "7908 MERGED 2026-09-25T07:27:34Z 70b3c9f1f8f0; 8013 MERGED 2026-09-25T11:01:34Z e5512ef66a74 titled Revert #7908"
  - claim: "Carrier heads cited in the new records are the gh-reported heads on 2026-10-11."
    command: "gh pr view <n> -R mastermindx-market-intelligence/macro --json headRefOid,headRefName,state,isDraft for n in 7976 8678 8039 7891 8002 7788 7804 8245 8250"
    result: "0a6e4d7f518d / ed1ceabd723c / c79aaca04948 / 861d4049ae4c / 508d8c206357 / 1f12d78169e1 / 3d286719686d / b019f975c695 / 20b853e2907e, all OPEN drafts (heads at read time; #8250 is superseded by its repair heads 20e7e9ac63759099704a46506e85b61d00b487fc and 1db9cad104437dc0c9bb4b27cf45781040302fb2, next entries)"
  - claim: "#8250's head at the 2026-10-11T04:05Z read was the repair head 20e7e9ac63759099704a46506e85b61d00b487fc (open draft; superseded by 1db9cad104437dc0c9bb4b27cf45781040302fb2, next entry, its only current head); its adjudication and repair-landed comments are the seat's, anchored MMX-GMI-INDUSTRIALS-T02-8250-ADJUDICATION and MMX-GMI-INDUSTRIALS-T02-8250-REPAIR-LANDED."
    command: "gh api repos/mastermindx-market-intelligence/macro/pulls/8250 --jq '[.head.sha,.state,.draft]|@tsv'; gh api repos/mastermindx-market-intelligence/macro/issues/comments/<id> --jq '[.user.login,.created_at]|@tsv' and --jq .body | grep -o 'MMX-GMI-INDUSTRIALS-T02-8250-[A-Z-]*' for id in 6105257496 6105272573"
    result: "20e7e9ac63759099704a46506e85b61d00b487fc open true; 6105257496: mastermindxryan 2026-10-11T04:03:00Z MMX-GMI-INDUSTRIALS-T02-8250-ADJUDICATION (VERDICT: REPAIR_REQUIRED at 20b853e2907e951a16304ff40d756ca707d2caab); 6105272573: mastermindxryan 2026-10-11T04:05:13Z MMX-GMI-INDUSTRIALS-T02-8250-REPAIR-LANDED (20e7e9ac)"
  - claim: "#8250 @20e7e9ac is RED on hosted checks (contract-delta, ci-pack-0, ci-gate) because origin/main's curated jobs nw-lobe-unfreeze and ticker-news-qbus reach industrials_profiles.py through issuer_profiles.py; the repair head 1db9cad104437dc0c9bb4b27cf45781040302fb2 (merge of origin/main f191b7f1 as 03d29dfea9d8 + two path lines) is on the PR head ref and the closure check is empty there."
    command: "gh run view 38110427910 -R mastermindx-market-intelligence/macro --job 114384660570 --log-failed | grep -c 'import closure now reaches engine/company_intelligence/industrials_profiles.py'; git -C <8250-worktree> merge-tree --write-tree --name-only 20e7e9ac origin/main; python3 -c 'from scripts.run_ci_pack import curated_exclusive_closure_findings as f; from pathlib import Path; print(dict(f(Path(\".github/ci/legacy-jobs.yml\"))))' (before and after the two lines); git push origin HEAD:refs/heads/codex/industrials-t02-issuer-enrollment-20260930-sol-001; git ls-remote origin refs/heads/codex/industrials-t02-issuer-enrollment-20260930-sol-001"
    result: "2 (nw-lobe-unfreeze, ticker-news-qbus); merge-tree clean rc=0 tree b94a9852aad1be2305d6dadc6626ec4935461486; before: {'nw-lobe-unfreeze': ['engine/company_intelligence/industrials_profiles.py'], 'ticker-news-qbus': ['engine/company_intelligence/industrials_profiles.py']}; after: {}; push rc=0; ls-remote 1db9cad104437dc0c9bb4b27cf45781040302fb2 (hosted checks pending at write time; one watcher bound)"
  - claim: "The Source Continuity verifier that refused at acc72f3f ran from Mastermind c7e47c859eb2 with the #982 census cap of 490, and the repository had 632 open PRs."
    command: "git -C <Mastermind main checkout> rev-parse HEAD; git -C <same> log -1 --format='%h %cI %s' -- scripts/source_continuity.py; grep -n _MAX_COLLISION_PRS scripts/source_continuity.py; gh api graphql -f query='{repository(owner:\"mastermindx-market-intelligence\",name:\"macro\"){pullRequests(states:OPEN){totalCount}}}'"
    result: "c7e47c859eb2925c5626931fd511800773ba09ac; 6eb1989d 2026-09-25T07:01:37Z fix(source-continuity): scale Macro census to 490 (#982); 77:_MAX_COLLISION_PRS = 490 and 1337: if len(pulls) > _MAX_COLLISION_PRS; {\"data\":{\"repository\":{\"pullRequests\":{\"totalCount\":632}}}} at 2026-10-11T05:12:45Z"
  - claim: "The open-PR roster stayed above the 490 cap after the census: 634 at 05:59Z and 633 at 06:17Z on 2026-10-11."
    command: "gh api graphql -f query='{repository(owner:\"mastermindx-market-intelligence\",name:\"macro\"){pullRequests(states:OPEN){totalCount}}}' (run at 05:59Z and again at 06:17Z)"
    result: "{\"data\":{\"repository\":{\"pullRequests\":{\"totalCount\":634}}}} at 2026-10-11T05:59:21Z; {\"data\":{\"repository\":{\"pullRequests\":{\"totalCount\":633}}}} at 2026-10-11T06:17:20Z"
  - claim: "#8002 (ENE-W1) is stacked on #7870 commit 6cd958e9 through its base branch and does not contain acc72f3f; the collision census's former 'none stacked' claim tested only containment of acc72f3f."
    command: "git merge-base acc72f3f 508d8c206357 (in the #7870 worktree with #8002's head fetched); git merge-base --is-ancestor 6cd958e9 origin/main; git merge-base --is-ancestor 6cd958e9 acc72f3f; git merge-base --is-ancestor acc72f3f 508d8c206357; git log -1 --format='%h %cI %s' 6cd958e9; gh api repos/mastermindx-market-intelligence/macro/pulls/8002 --jq '[.base.ref,.head.sha,.state,.draft]|@tsv'; python3 -c 'import json; d=json.load(open(\"census3.json\")); print(sorted(d[\"summary\"][\"colliding\"][0].keys()))'"
    result: "6cd958e92b259f7221690547e7076f4a0de4ed33; NOT_ON_MAIN; ON_7870; 8002_LACKS_acc72f3f; 6cd958e92b25 2026-09-24T22:27:25-07:00 [DRAFT/HOLD] semiconductor-b hook 4b fix: a second vertical's remembered tab now comes back; claude/energy-stack-base-b-6cd958e9 508d8c206357287a5f8ff9d1596efc32b3749459 open true; ['base', 'collisions', 'compare_status', 'contains_acc72f3f', 'draft', 'files_censused', 'head', 'number'] (no earlier-commit stacking field), so #8002 with 0 own-path collisions against its stacked base is outside the 190 by construction; the per-PR census projection is durable in #7870 comment 6106134520 section 3"
  - claim: "The #7870 x #8250 collision resolves to three conflicting hunks in issuer_profiles.py and none in legacy-jobs.yml at both #8250 heads, 20e7e9ac and the current 1db9cad1."
    command: "git merge-tree --write-tree acc72f3f 20e7e9ac and git merge-tree --write-tree acc72f3f 1db9cad104437dc0c9bb4b27cf45781040302fb2 (in the #7870 worktree, both heads fetched); git show <tree>:engine/company_intelligence/issuer_profiles.py | grep -c '^<<<<<<<'; same for .github/ci/legacy-jobs.yml and tests/test_ci_pack.py; git diff --name-only 363b4e62 f191b7f1 -- tests/test_ci_pack.py .github/ci/legacy-jobs.yml; git diff --name-only f191b7f1 1db9cad1"
    result: "at 20e7e9ac: tree 8a957225cc5ca8c3cd589552b336882c38c826af; at 1db9cad1: tree 71af057ff8c656f3bf72ab57aec01e5af8984fd3 (the short-SHA spelling gives 5b48480be7df630acb683f3880b23442b9fd7155, identical except for the >>>>>>> labels); both rc=1 with the single CONFLICT (content): Merge conflict in engine/company_intelligence/issuer_profiles.py and .github/ci/legacy-jobs.yml auto-merged; markers 3 / 0 at both, and 0 in tests/test_ci_pack.py at 1db9cad1, which auto-merges there as a main-side change (both paths are listed by the 363b4e62..f191b7f1 diff), not an #8250-owned path; #8250's own diff against f191b7f1 is 7 paths: .github/ci/legacy-jobs.yml, engine/company_intelligence/industrials_profiles.py, engine/company_intelligence/issuer_profiles.py, research/industrials/first_vertical_program/requirement_index.md, tests/industrials_result_cash_helpers.py, tests/test_industrials_dependency_binding.py, tests/test_industrials_issuer_enrollment.py"
  - claim: "The Mining T02 gate condition (#7905 on main) is satisfied: cdce3023fbba is an ancestor of main a4d48836a69e and the fiscal_scope seam is present there."
    command: "git merge-base --is-ancestor cdce3023fbba a4d48836a69e && echo ANCESTOR_YES; git show a4d48836a69e:engine/company_intelligence/issuer_profiles.py | grep -n fiscal_scope"
    result: "ANCESTOR_YES; 4 hits: :1294 (the fiscal_scope kwarg in the profile_for_ticker signature whose def is at :1293), :1306, :1307, :1309 (the private PG guard)"
  - claim: "#8245 comment 5927055846 is an issue comment rather than a GitHub review object, and #8245 still sits at b019f975c695."
    command: "gh api repos/mastermindx-market-intelligence/macro/issues/comments/5927055846 --jq '[.user.login,.created_at]'; gh pr view 8245 -R mastermindx-market-intelligence/macro --json reviewDecision,reviews,headRefOid,isDraft,state"
    result: "mastermindx-3, 2026-10-01T07:44:02Z; reviewDecision empty, reviews [], head b019f975c6959803e872fd5000601d6c4591bf62, Draft, OPEN (read 2026-10-11)"
  - claim: "The fresh non-author review of the b76551be..acc72f3f delta is in hand on the #7870 carrier."
    command: "gh api repos/mastermindx-market-intelligence/macro/issues/comments/6105402719 --jq .body | grep -n -E 'Verdict|ACCEPT_DELTA'"
    result: "line 8: Verdict: ACCEPT_DELTA (PASS, scope = the two-file delta only), independent READ_ONLY Opus; anchor MMX-GMI-SEMICONDUCTOR-B-7870-DELTA-REVIEW-CONSUMED-acc72f3f-20261011"
unverified:
  - claim: "At acc72f3f tests/test_finance_research_registration.py also passes 100 with the four shared-shell modules forced absent."
    what_would_verify: "A recorded command that makes the shared-shell modules unimportable for one pytest run (for example a sys.modules/meta_path block) and its literal result. No such command is recorded anywhere, so the claim was removed from the DEC:SEMICONDUCTOR-B-H1-FINANCE-ADAPTER-HOLDS-SECTOR-PROFILE evidence list on 2026-10-11."
  - claim: "Hosted ci-pack-8 and ci-gate are green at acc72f3f."
    what_would_verify: "The ALL_CONCLUDED table of the one verifiably live (or newly bound) CI watcher for the exact head acc72f3f, then one fresh gh pr view read of the same head before any Ready or merge transition."
  - claim: "The Energy #8002 arity patch (12 -> 14 kwargs at tests/test_nuclear_research_route.py:27) is the only Energy breakage once #7870 lands."
    what_would_verify: "A head-vs-base pytest diff of tests/test_nuclear_research_route.py on #8002 rebased onto a main that contains #7870."
  - claim: "The Codex child's writer lease on codex/industrials-t02-issuer-enrollment-20260930-sol-001 is inert, so the seat's two pushes (20e7e9ac, 1db9cad1) did not duplicate a live writer."
    what_would_verify: "A read of that child's RuntimeBinding and lease in Executive OS through the authenticated mastermind-executive connector (unreachable from this seat on 2026-10-11). The pushes rest on Ruling C-1 of DECISION 6105015260 plus the recorded exception in #8250 comment 6105257496 line 22, with Sol's CONTINUE 5925110889 (2026-10-01T05:04Z) as the last child-side edge; the custody reconciliation is owed before #8250's Ready or merge."
unresolved:
  - "Chairman has not yet confirmed whether the Theme-Graph GMI D2E/W3B/W3C lane with a live Astra principal (#8540, #8753, #8711, #8324) moves under this seat or stays with Astra; the records keep it observe-only."
  - "The Executive/Subagent Fabric is under repair (Mastermind PRs 1300-1319 open except 1305); the mastermind-executive and linear-server MCP connectors need user OAuth and mmx-cimd-probe refuses connections, so no fabric packet can be submitted from this seat yet."
  - "Option A (registry entry_kind) is scoped in the H1 DEC but has no carrier branch yet (SB-W2 todo)."
next_actions:
  - "Landing order is binding (#7870 comment 6105402719 line 18): Industrials #8250 (head 1db9cad104437dc0c9bb4b27cf45781040302fb2, adjudicated 6105257496, repaired at 20e7e9ac per 6105272573 and again at 1db9cad1 for the curated-closure red of run 38110427910) lands on main first once, at 1db9cad1, ALL_CONCLUDED green from the one bound watcher, the non-author READ_ONLY review chain 20b853e2..20e7e9ac (ACCEPT_MANIFEST_COMMIT, #8250 comment 6105272573) and 20e7e9ac..1db9cad1 (ACCEPT_REPAIR, #8250 comment 6106321419; the merge commit 03d29dfe against each parent plus the two-line commit), gate (4) applied to #8250 in its own terms (a verifier run at #8250's own release head from protected Mastermind master at re-run time with --external-effect-evidence-fingerprint = sha256 of #8250's recorded external-effect artifact, da6a8c45d80757e2ef3eda821dd56e24db64149c92e8a6c6d3bb231846cc0c06 at 1db9cad1, quoted verbatim in a #8250 DECISION; or a non-seat acceptance by cited id of #8250's own substitute recorded at 1db9cad1 in #8250 comment 6106395498), and the custody reconciliation (WS:GMI-INDUSTRIALS-FIRST-VERTICAL next_action) are all in hand (status at the pushed head of this records PR: green at 1db9cad1, ALL_CONCLUDED 2026-10-11T06:24:44Z, and the review chain are in hand; gate (4) and custody are owed); #7870 then merges main (the comment's 'rebases afterward' is implemented as a merge of main into the branch, no history rewrite) and resolves its two-path collision set with #8250 (engine/company_intelligence/issuer_profiles.py, three conflicting hunks per git merge-tree --write-tree acc72f3f 20e7e9ac and acc72f3f 1db9cad1 and grep -c '^<<<<<<<' on each result tree; .github/ci/legacy-jobs.yml auto-merged). Green and the delta review at acc72f3f are evidence for the pre-merge tree only. Still owed at the post-merge head before the release DECISION: one further non-author READ_ONLY read of the merge resolution (the merge commit diffed against each parent, not the base-inclusive range acc72f3f..<new head>), ALL_CONCLUDED green from exactly one watcher bound to that head, and a BINDING re-run of the Source Continuity verifier from protected Mastermind master at re-run time with its SHA recorded in the DECISION and --external-effect-evidence-fingerprint = sha256 of the recorded external-effect artifact (the git ls-remote line plus the pulls/7870 head/state/draft read at the release head, not the census), quoted verbatim: REMOTE_COMPLETE_VERIFIED puts gate (4) in hand; any refusal is RELEASE_BLOCKED unless the Chairman or Sol accepts the recorded substitute on #7870 by a cited comment or message id before the DECISION, and that acceptance is narrowed by #7870 comment 6106134520 to roster-size REMOTE_CENSUS_INCOMPLETE only (scripts/source_continuity.py:77, :1337; the verifier does not report the cause, the code is one static text emitted from several sites, and the :2614-2615 attribution for acc72f3f is the seat's inference, so roster size is shown only by the attribution test recorded in SB-W1 gate (4) of WS:GMI-SEMICONDUCTORS: fresh open-PR counts above 490 immediately before and after the run, paginated pulls/N/files == git diff --name-only, the run inside the census budget, any doubt RELEASE_BLOCKED), re-recorded at the exact release head and quoted in the DECISION, with every other refusal code RELEASE_BLOCKED regardless (the seat requested that ruling in #7870 comment 6106057199, narrowed it in 6106134520 and does not rule; at acc72f3f the verifier returned REMOTE_CENSUS_INCOMPLETE because the repository had 632 open PRs (634 at 05:59Z, 633 at 06:17Z) against the protected adapter cap of 490, which only the Mastermind #346 series or open-PR cleanup can change; SB-W1 gate (4) in WS:GMI-SEMICONDUCTORS records the evidence; #8002 (ENE-W1) is stacked on #7870 commit 6cd958e9 and is retargeted to main only after #7870 lands). Then a fresh carrier read before every post and act, ONE release DECISION per the DEC-FABLE-SEAT order, then Ready and merge queue, each asserting the exact head. On red at any head: repair in scope, re-bind the watcher, extend the non-author review to the repair delta. On HEAD_CHANGED: re-read before anything."
  - "Open the Option A registry carrier (SB-W2) off a main that contains #7870; it must forward view_keys/build_query from FINANCE_REGISTRATION_FACTS and must not reintroduce any xfail on the round trip."
  - "Dispatch the held wave-2 packets once the fabric accepts submissions, in this order: P-FIN-1, CDV-T4, Energy-1 arity patch, Tech-1, Robotics-1 re-land, CC-1, P-IND-1, P-MIN-1, HC-1. #8250 is not a fabric packet: it is adjudicated (6105257496), repaired at 20e7e9ac (6105272573) and again at 1db9cad1 (its current head; a repair-landed note at 1db9cad1 is owed on #8250 once green), and lands first on the #7870 release path above."
  - "Append the #7870 outcome and the records PR number to the Semiconductors record (SB-W1 status) in a follow-on records PR."
do_not_redo:
  - "Do not re-litigate H1; ruling B is implemented at acc72f3f and the Opus audit of b76551be is consumed. The H1 ruling itself is not re-audited; the non-author review of the b76551be..acc72f3f delta is in hand (#7870 comment 6105402719). What remains owed before release is the non-author read of the post-#8250 merge resolution, green at that head, and gate (4): the binding Source Continuity re-run (REMOTE_COMPLETE_VERIFIED) or a non-seat acceptance of the recorded substitute on #7870 by cited id under the narrowed rule of #7870 comment 6106134520 (roster-size REMOTE_CENSUS_INCOMPLETE only, re-recorded at the exact release head and quoted in the DECISION, #8250 covered only by its own substitute); the seat does not self-rule that gate."
  - "Do not re-add an xfail(raises=ValueError) on test_shared_shell_registration_roundtrip_pinned_to_7870; FinanceRegistrationRefusal subclasses ValueError and the marker absorbs the real defect."
  - "Do not treat Robotics as merged; #8013 reverted #7908. Re-landing is ROB-W2."
  - "Do not edit WS-GMI-THEME-GRAPH.md from this seat while the Astra lane is live; it is observe-only until the Chairman rules."
  - "Do not poll a CI watcher or run gh run watch; do not stack a second watcher on a head while one is verifiably live (control_plane owns liveness); if none is live, bind exactly one."
danger_areas:
  - "engine/theme_graph/store.py and templates/basket_detail.html.j2 are frozen by #7462 and #7669; no product code on #7780 / #7773 / #7462 / #7669."
  - "The macro repository is PUBLIC; never commit paid research payloads, credentials or private screenshots, and never create a new private store."
  - "Never mutate git in the main checkout and never open the Macro Dashboard checkout as a workspace; all records work happens in the SSD worktree."
  - "The git stash stack is shared across sessions; never use bare git stash or git stash pop."
---

## Why this handoff exists

The consolidation changed who answers for eleven verticals, and five of them had no durable
record at all. This file is the single place the next seat reads to learn which carrier is on
the critical path (#7870 at acc72f3f), what is already ruled (H1-B), what is held (fabric
packets), and what is deliberately not touched (the Astra Theme-Graph lane).
