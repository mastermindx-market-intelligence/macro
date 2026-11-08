---
workstream: "WS:GMI-SEMICONDUCTORS"
session: "claude/ssd-semiconductor-theme-intelligence-b-bd3685-eb0b7a4bbaaca77d (Fable 5.1 Meta-CEO seat; #7870 worktree semiconductor-theme-intelligence-b-impl-988406e131fd90b9; records worktree industry-intelligence-records-followon-71cab469f9a4b984)"
model: fable
ended_because: ci_handoff
prs: [7870]
decisions:
  - "DEC:CHAIRMAN-INDUSTRY-INTELLIGENCE-META-CEO-CONSOLIDATION-2026-10-11"
  - "DEC:SEMICONDUCTOR-B-H1-FINANCE-ADAPTER-HOLDS-SECTOR-PROFILE"
discoveries:
  - "DSC:SOURCE-CONTINUITY-CENSUS-PASS-CRITERION-FOR-MACRO-CARRIERS-OVER-THE-490-CAP"
mission: >
  Same Chairman directive as the 2026-10-11 meta-ceo-consolidation handoff. This window: keep
  #7870 mergeable against a moving origin/main without rewriting history, have every head move
  read by a non-author READ_ONLY reviewer, and leave the release gates stated as what they are
  (non-seat rulings and a CI-contract acceptance), not as waits on CI.
state_before: >
  #7870 at acc72f3f (H1 ruled B, delta review ACCEPT_DELTA in #7870 comment 6105402719), one
  CI watcher bound, RELEASE_BLOCKED on gate (4). origin/main moved twice under it (3ab976f5 =
  #8771, then c50af4eb), each time extending the closure lists of the same seven
  `scope: exclusive` jobs in .github/ci/legacy-jobs.yml that #7870 also extends, and each time
  moving the tests/test_ci_pack.py PACKING_PROBES rows that #7870 also touches.
changed:
  - path: .github/ci/legacy-jobs.yml
    what: >
      Macro PR 7870 heads ad5bdb2c (base-sync 1, merge of origin/main 3ab976f5 into acc72f3f)
      and 1eb871d6 (base-sync 2, merge of origin/main c50af4eb into 36e2064d). At 1eb871d6 the
      seven conflict hunks resolve as the union of both sides' closure lists (carrier block then
      main block; no path dropped); 278 jobs parse at that head (blob a080e1f4). Head
      839bd6a1b065959b90e48d3171edbbe85f4f74f3 (CI repair, +6 lines, no other file): the union made
      semiconductor-b-boundary's import closure reach site/turn_watch/turn_watch.json (a file
      neither parent reached alone, through app.main -> app.prophet_observations), so the job's
      paths: now lists it with a dated comment; 278 jobs parse, the job lists 141 paths.
  - path: tests/test_ci_pack.py
    what: >
      Same heads. PACKING_PROBES rows raised to keep each probe inside the packing bound after the
      union: templates/index.html 5_800 -> 5_801 (ad5bdb2c) -> 5_827 (1eb871d6);
      scripts/build_free_content.py 5_600 -> 5_602 (1eb871d6); dated docstring entries record each
      raise with per-side measurements. Both raises are RECORDED by the seat and NOT accepted by
      the CI-contract owner. In between, 2b770ade (docstring-only, +23/-6) drew REQUEST_REPAIR from
      the READ_ONLY read and 36e2064d repaired every item ("Repaired in full" in the read consumed
      as #7870 comment 6111839715). Unchanged at 839bd6a1.
  - path: app/deploy/update.sh
    what: >
      1eb871d6 only: the deploy trigger line is main's line with the carrier's substitution
      applied (combined; no path dropped); bash -n OK at that head (blob 7a86b42d).
  - path: agentos/workstreams/WS-GMI-SEMICONDUCTORS.md
    what: >
      This records PR. SB-W1 carries the head progression acc72f3f -> ad5bdb2c -> 2b770ade ->
      36e2064d -> 1eb871d6 -> 839bd6a1 with the review chain by comment id, the
      watcher-registration trap inside gate (3), the superseded Source Continuity substitute
      inside gate (4), the recorded-not-accepted raises as gate (5), five new do_not_redo lines,
      the DSC citation, the CI red at 1eb871d6 with its repair head 839bd6a1, hosted green at
      839bd6a1 (check-runs read 19:24:07Z; #7870 comment 6112888232) and the body state lines at
      that head; SB-W3 carries the R-ENE-07 queue item and a new landmine names #8245 as the
      single private_publication.py writer.
  - path: agentos/discoveries/DSC-SOURCE-CONTINUITY-CENSUS-PASS-CRITERION-FOR-MACRO-CARRIERS-OVER-THE-490-CAP.md
    what: >
      New. The five-leg substitute criterion the seat has requested (not ruled) for gate (4) on
      #7870 and #8250 while the open-PR roster exceeds the 490 cap, its falsifier (a non-seat
      ruling that accepts less, or requires
      the receipt) and the #346 envelope figures.
  - path: agentos/workstreams/WS-GMI-INDUSTRIALS-FIRST-VERTICAL.md
    what: >
      One dated line in next_action recording the seat's own reading of #8250's gate (4) against
      the requested, still unruled five-leg substitute criterion (the DSC; a request, not a
      ruling) and which legs 6106395498 satisfies by that reading; no other change to the #8250
      state.
  - path: agentos/workstreams/WS-GMI-ENERGY-NUCLEAR.md
    what: >
      One landmine and one dated next_action sentence recording the seat's R-ENE-07 answer (#7870
      comment 6112888232): the REGULATORY_MILESTONE enum is queued under SB-W3 (V1.1) with Energy's
      admission terms, Energy retains the milestone under limitations.establishes meanwhile
      (R-ENE-07(b)), and #8245 is the single writer of the generic private projection role in
      engine/earnings_narrative/private_publication.py.
verified:
  - claim: "#7870 branch ref, local HEAD and tree agree at 1eb871d6e504bf141367582dfa1d58d115882204 and the worktree is clean."
    command: "git ls-remote origin refs/heads/claude/ssd-semiconductor-theme-intelligence-b-impl-988406e131fd90b9; git rev-parse HEAD 'HEAD^{tree}'; git status --porcelain | wc -l"
    result: "2026-10-11T17:35:58Z: 1eb871d6e504bf141367582dfa1d58d115882204 on both; tree 73640ee5c405727d50e441e0939dc24613780d02; 0 dirty paths"
  - claim: "At 1eb871d6 the packing-probe job selection is identical to base 3ab976f5, carrier 36e2064d and main c50af4eb on all three probes, and each parent alone is under its own ceiling table."
    command: "/opt/homebrew/bin/python3 probe_rev.py <root> for each of the four trees (loads that tree's own scripts/run_ci_pack.py via importlib and runs packing_probe_measurements on its own .github/ci/legacy-jobs.yml with the three PACKING_PROBES rows, max_packs=10; the three non-merged trees were checked out detached in the records worktree and restored); then compare.py over the four JSON files"
    result: "only_in_* empty for every pair and probe; weights templates/index.html 5770/5801/5796/5827 (135 jobs), scripts/build_free_content.py 5560/5591/5571/5602 (133), engine/prophet/plan_book.py 5520/5551/5531/5562 (128) for base/carrier/main/merged; packs 10 everywhere; that side's own ceilings base 5800/5600/5600, carrier 5801/5600/5600, main 5800/5600/5600, merged 5827/5602/5600"
  - claim: "The non-author READ_ONLY Opus read of 36e2064d..1eb871d6 (scope A docfix-2, scope B merge resolution against each parent) returned ACCEPT and was consumed on the carrier."
    command: "Agent(model: opus, ROUTE: AUDIT, MODE: READ_ONLY) over the bundle; verdict extracted with verdict-extract.py <src> <dst>; gh api repos/mastermindx-market-intelligence/macro/issues/comments/6111839715 --jq '[.id,.created_at,(.body|length),(.body|split(\"\\n\")[0])]|@tsv'"
    result: "AUDIT_VERDICT: PASS / VERDICT: ACCEPT ('covers only the two scopes asked; does not accept the ceiling raises, the release or deployment'); SCOPE_A Repaired in full; SCOPE_B checks 1-5 PASS; findings 1 MINOR (settled by the per-side measurement), 1 MAJOR (the ceiling-raise acceptance gate), 4 NOTE; readback 6111839715 2026-10-11T17:43:02Z 7454 chars, first line MMX-GMI-SEMIS-7870-DELTA-REVIEW-CONSUMED-1eb871d6e504-20261011"
  - claim: "Syntax checks are stamped at HEAD 1eb871d6."
    command: "bash -n app/deploy/update.sh; /opt/homebrew/bin/python3 -c 'import ast; ast.parse(open(\"tests/test_ci_pack.py\").read())'; /opt/homebrew/bin/python3 -c 'import yaml; print(len(yaml.safe_load(open(\".github/ci/legacy-jobs.yml\"))[\"jobs\"]))'"
    result: "OK; OK; 278 (blobs 7a86b42d / 4fcfc34c / a080e1f4 at 17:35:58Z)"
  - claim: "The templates/index.html weight ceiling never changed on origin/main before this carrier; only the job-count column moved."
    command: "git log --format=%h -G'\"templates/index.html\", [0-9_]*, [0-9_]*' origin/main -- tests/test_ci_pack.py; for each hash: git show <h>:tests/test_ci_pack.py | grep -o '(\"templates/index.html\", [0-9_]*, [0-9_]*)'"
    result: "9 commits 69268b06 (2026-08-23) .. 55e8cf84 (2026-10-07, #8596), every one at 5_800, job column 129 -> 135; scripts/build_free_content.py: 6 commits, every one at 5_600, job column 130 -> 134"
  - claim: "The first CI watcher at 1eb871d6 concluded falsely at its first tick, before the ci-pack matrix registered."
    command: "cat watch-7870-1eb871d6.log; gh api 'repos/mastermindx-market-intelligence/macro/commits/1eb871d6e504bf141367582dfa1d58d115882204/check-runs?per_page=100' --jq '.check_runs[]|[.status,.conclusion,.name,.started_at]|@tsv' (17:22:59Z)"
    result: "tick 1 17:14:12Z total=3 pending=0 -> ALL_CONCLUDED with only ci-authority, ci-authority/main and merge-queue-pilot present; at 17:22:59Z 25 check runs: ci-plan success (17:14:52Z-17:15:52Z), ci-pack-0..11 and contract-delta in_progress (started 17:15:54-55Z), fence-pack / capability-broker / grader-manifest / self-mod-fence success, trusted-ci skipped, merge-queue-pilot failure (non-gating per 6107602010)"
  - claim: "The carrier had no comment newer than 6111593948 at the moment the consuming note was posted."
    command: "gh api 'repos/mastermindx-market-intelligence/macro/issues/7870/comments?per_page=100&since=2026-10-11T17:15:56Z' --jq '.[] | select(.id > 6111593948) | .id' | wc -l, gated with [ \"$newer\" -eq 0 ] || exit 3 before the post"
    result: "0 at 2026-10-11T17:43:01Z; post returned 6111839715 at 17:43:02Z"
  - claim: "Workflow run 38158831326 at 1eb871d6 concluded RED on exactly three gating checks plus the non-gating merge-queue pilot, all naming one introduced closure defect."
    command: "gh api 'repos/mastermindx-market-intelligence/macro/commits/1eb871d6e504bf141367582dfa1d58d115882204/check-runs?per_page=100' --jq '.check_runs[]|[.status,.conclusion,.name,.id]|@tsv'; gh api --allow-escape-sequences repos/mastermindx-market-intelligence/macro/actions/jobs/114527295194/logs | sed 's/\\x1b\\[[0-9;]*[A-Za-z]//g' | grep -n 'semiconductor-b-boundary\\|introduced' (contract-delta); gh api --allow-escape-sequences repos/mastermindx-market-intelligence/macro/actions/jobs/114527512551/logs | sed 's/\\x1b\\[[0-9;]*[A-Za-z]//g' | grep -n 'CI_PACK_FAILED_JOBS\\|test_ci_pack.py:4717\\|passed in' (ci-pack-0, the ci-control-plane-contracts pack), then the same ANSI-stripped log saved whole as cipack0-114527512551.log (876 lines, session-local, not in this PR) read with sed -n '548,551p;587p;595p;605p;825,828p' for the figures the grep cannot print: 548 '1 failed, 592 passed in 395.82s', 550 the step exited-1 error, 551 'HEAD is now at 14a168e6a Merge 1eb871d6... into 216254bf...', 587 'HEAD is now at 216254bf6', 595 the step group header for the base re-run, 605 '593 passed in 399.35s', 825-828 CI_PACK_FAILED_JOBS, 'Legacy CI failures', the exited-1 line and 'Process completed with exit code 1'; and the local reproduction in the #7870 worktree, /opt/homebrew/bin/python3 -m pytest tests/test_ci_pack.py -k test_curated_exclusive_scopes_cover_their_own_import_closure -q -p no:cacheprovider, saved as repro-closure-test.txt (17:56:30Z)"
    result: "check-runs read: contract-delta job 114527295194, ci-pack-0 job 114527512551 and ci-gate job 114534400922 concluded failure, plus the non-gating merge-queue pilot; contract-delta log, step 7: 'semiconductor-b-boundary: import closure now reaches site/turn_watch/turn_watch.json, which .github/ci/legacy-jobs.yml's declared paths: for semiconductor-b-boundary does not cover' and 'contract-delta: 1 introduced, 0 inherited (base 216254bf6070)'; ci-pack-0 log (job 114527512551, pack ci-control-plane-contracts): step 'hosted-runner packing contract' at the merge commit 14a168e6a (1eb871d6 into base 216254bf): tests/test_ci_pack.py:4717 AssertionError, assert not {'semiconductor-b-boundary': ['site/turn_watch/turn_watch.json']}, 1 failed, 592 passed in 395.82s (17:26:17Z); the same step re-run by the runner at base 216254bf6 alone: 593 passed in 399.35s (17:37:14Z), so the failure is introduced by the PR, not inherited; verdict CI_PACK_FAILED_JOBS=[ci-control-plane-contracts], 'Legacy CI failures: ci-control-plane-contracts: step hosted-runner packing contract exited 1', process exit 1 (17:41:18Z); local reproduction repro-closure-test.txt: the same :4717 assertion, 1 failed, 167 deselected in 457.82s"
  - claim: "The defect is union-only: the job does not exist on origin/main and the reach path is main-side code imported through the carrier's transport suites."
    command: "for r in 216254bf c50af4eb e3ee3dcb 36e2064d HEAD; do git show $r:.github/ci/legacy-jobs.yml | grep -c '^  semiconductor-b-boundary:'; done; git cat-file -e 36e2064d:app/prophet_observations.py (exit 128 = absent); grep -n 'app.main\\|prophet_observations\\|turn_watch' tests/test_theme_research_api.py tests/test_semiconductor_witness_served_proof.py app/main.py app/prophet_observations.py"
    result: "0 0 0 1 1; tests/test_theme_research_api.py (5 refs) and tests/test_semiconductor_witness_served_proof.py (2 refs) import app.main; app/main.py:2371 imports app.prophet_observations (absent at 36e2064d: git cat-file -e exits 128); app/prophet_observations.py:61 names _DATA_ROOT.parent / 'site/turn_watch/turn_watch.json'"
  - claim: "The closure test is red at 1eb871d6 and green after the one-line widening, on the same interpreter, with the packing probes unchanged."
    command: "cd <#7870 worktree>; /opt/homebrew/bin/python3 -m pytest tests/test_ci_pack.py -k test_curated_exclusive_scopes_cover_their_own_import_closure -q -p no:cacheprovider (before and after the edit); /opt/homebrew/bin/python3 probe_rev.py <root> <out.json> on the repaired tree"
    result: "before: 1 failed, 167 deselected in 457.82s (17:56:30Z-18:04:25Z), assert not {'semiconductor-b-boundary': ['site/turn_watch/turn_watch.json']}; after: 1 passed, 167 deselected in 252.99s (18:05:17Z-18:09:31Z); probes templates/index.html 135/5827, scripts/build_free_content.py 133/5602, engine/prophet/plan_book.py 128/5562, packs 10, identical to 1eb871d6 (measured 18:08:57Z-18:13:20Z on the working tree with the widening applied but not yet committed, so probes-after.txt is stamped with the parent 1eb871d6e504 tree 73640ee5c405; the commit is 18:18:43Z)"
  - claim: "The repair head is pushed and the consuming note is on the carrier with no newer comment at post time."
    command: "git ls-remote origin refs/heads/claude/ssd-semiconductor-theme-intelligence-b-impl-988406e131fd90b9; git rev-parse HEAD; gh api 'repos/mastermindx-market-intelligence/macro/issues/7870/comments?per_page=100&since=2026-10-11T17:43:03Z' --jq '[.[]|select(.id!=6111839715)]|length' gated with || exit before the post; readback of the posted id"
    result: "839bd6a1b065959b90e48d3171edbbe85f4f74f3 on both; newer_comments=0 at post time; note 6112182784 (anchor MMX-GMI-SEMIS-7870-CI-RED-CONSUMED-1eb871d6-REPAIR-839bd6a1b065-20261011)"
  - claim: "The non-author READ_ONLY Opus read of the repair delta 1eb871d6..839bd6a1 returned ACCEPT scoped to that delta only and was consumed on the carrier."
    command: "Agent(model: opus, ROUTE: AUDIT, MODE: READ_ONLY) over the repair packet (patch, job block at 839bd6a1, per-rev job presence, app.main import lines, prophet_observations lines 50-70, transport-suite imports, CI error lines of run 38158831326, local red and green closure-test runs, post-repair probes); verdict extracted with verdict-extract.py <src> <dst>; fresh-read gate newer-than-6112182784 == 0 and pulls/7870 head == 839bd6a1 with || exit; gh api ... -X POST -F body=@file --jq .id; readback by id"
    result: "VERDICT: ACCEPT ('does NOT accept hosted CI at 839bd6a1, merging PR #7870, any release, any ceiling raise, or any deployment'); one additive +6 hunk inside the job's paths list, 141 path entries, YAML-safe, tool-prescribed minimal fix; caveat: post-repair probes labelled with the parent SHA because the tree was dirty when measured. Consumed as #7870 comment 6112221196 (anchor MMX-GMI-SEMIS-7870-REPAIR-DELTA-READ-CONSUMED-839bd6a1b065-20261011) at 2026-10-11T18:24:41Z."
  - claim: "The Agent OS validator stays at zero errors with this PR's records."
    command: "/opt/homebrew/bin/python3 scripts/agentos.py validate"
    result: "agentos: 1647 records (91 workstreams, 439 decisions, 486 discoveries, 631 handoffs) — 0 error(s), 153 warning(s), run at 6996c224, again on the ad393681 tree, again on the tree committed as 4a540c44 (the second re-read's repairs) and again on the working tree after the R-ENE-07 edits and before the second commit, i.e. the exact content committed as 965315b3, each run after every edit in that commit and before it; baseline at b5cafed6 was 1645 records, 0 error(s), 153 warning(s). The one interim error (DSC falsifier without a runnable token, README rule 4) was fixed by citing #7870/#8250 and scripts/source_continuity.py in the falsifier before commit."
  - claim: "One v2-guarded CI watcher was launched for 839bd6a1 and was still alive 34 and 43 minutes later."
    command: "watch-checks-v2.sh 7870 839bd6a1b065959b90e48d3171edbbe85f4f74f3 150 96 (background; writes watch-7870-839bd6a1-v2.log and .pid); head -2 watch-7870-839bd6a1-v2.log; ps -o command= -p 37757; kill -0 37757; ps -o lstart= -p 37757 (prints host-local time; host TZ PDT, UTC-7)"
    result: "pid 37757; log header 'WATCH #7870 head=839bd6a1b065959b90e48d3171edbbe85f4f74f3 interval=150s start=2026-10-11T18:19:32Z', tick 1 at 18:19:33Z total=9 pending=3; ps shows that launch command; kill -0 exit 0 at 18:53:21Z and again at 19:02:12Z, same argv; ps lstart 'Sun Oct 11 11:19:32 2026' PDT = 18:19:32Z, equal to the log header's start. The session-native Monitor armed on this log is a tool watch with no shell command and is not evidence here; the watcher printed ALL_CONCLUDED at 19:22:18Z after tick 26 (total=26, pending=0) and exited: kill -0 37757 at 19:22:56Z reported no such process, and ps -o lstart= at 19:22:39Z printed nothing for the same reason"
  - claim: "On 2026-10-11, 82 PRs merged through 19:06:43Z, every one with base main, and the open-PR roster was 642 at 19:02:49Z: the roster is above the 490 cap, and carriers outside the seat's gate set (#7870, #8250) keep merging."
    command: "gh api --paginate 'repos/mastermindx-market-intelligence/macro/pulls?state=closed&sort=updated&direction=desc&per_page=100' --jq '.[] | select(.merged_at != null) | select(.merged_at|startswith(\"2026-10-11\")) | [.number,.merged_at]|@tsv' | sort -k2 | sed -n '1p;$p' and the same pipeline piped to wc -l (read 19:01:15Z, no base filter); then gh api --paginate 'repos/mastermindx-market-intelligence/macro/pulls?state=closed&base=main&sort=updated&direction=desc&per_page=100' --jq '.[] | select(.merged_at != null) | select(.merged_at|startswith(\"2026-10-11\")) | [.number,.merged_at,.base.ref]|@tsv' piped to wc -l and to sort -k2 | sed -n '1p;$p' (read 19:11:32Z), and the same pipeline without base=main piped to cut -f3 | sort | uniq -c (read done 19:13:02Z); gh api graphql -f query='query{repository(owner:\"mastermindx-market-intelligence\",name:\"macro\"){pullRequests(states:OPEN){totalCount}}}' --jq '.data.repository.pullRequests.totalCount' (read 19:02:49Z)"
    result: "first read, no base filter: 78 merged PRs, first #8755 at 00:57:36Z, last #8852 at 19:01:12Z; base=main read: 82, first #8755 at 00:57:36Z, last #8837 at 19:06:43Z; any-base read: 82 with .base.ref uniq -c = 82 main (the two reads differ only by the four merges between 19:01Z and 19:07Z); totalCount 642"
  - claim: "acc72f3f and 36e2064d each concluded hosted with 21 success, 4 skipped and one failure, the merge-queue pilot, which #7870 comment 6107602010 records as non-gating; the command lists conclusions and failed-check names, not which checks gate."
    command: "for s in acc72f3fb3efb1ad092359ce2ba4190de66d75e1 36e2064d5639e8bb7d96617afb7a236be14619bb; do gh api --paginate \"repos/mastermindx-market-intelligence/macro/commits/$s/check-runs?per_page=100\" --jq '.check_runs[] | [.status,.conclusion]|@tsv' | sort | uniq -c; gh api --paginate \"repos/mastermindx-market-intelligence/macro/commits/$s/check-runs?per_page=100\" --jq '.check_runs[] | select(.conclusion==\"failure\") | [.name,.html_url]|@tsv'; done"
    result: "acc72f3f (read 19:13:04Z, the seat's own log timestamp, not reproducible from the carrier): 21 completed success, 4 completed skipped, 1 completed failure = ci-authority/codex/merge-queue-pilot check run 114379982885; 36e2064d (read 19:13:06Z, the seat's own log timestamp, not reproducible from the carrier): 21 success, 4 skipped, 1 failure = ci-authority/codex/merge-queue-pilot check run 114439966726"
  - claim: "839bd6a1 concluded hosted with 21 success, 4 skipped and one failure, the same merge-queue pilot (non-gating per #7870 comment 6107602010); the v2 watcher bound to it printed ALL_CONCLUDED and exited."
    command: "gh api --paginate \"repos/mastermindx-market-intelligence/macro/commits/839bd6a1b065959b90e48d3171edbbe85f4f74f3/check-runs?per_page=100\" --jq '.check_runs[] | [.status,.conclusion]|@tsv' | sort | uniq -c; the same read with --jq '.check_runs[] | select(.conclusion==\"failure\") | [.name,.html_url]|@tsv'; grep -n ALL_CONCLUDED watch-7870-839bd6a1-v2.log; sed -n '/ALL_CONCLUDED/,$p' watch-7870-839bd6a1-v2.log | tail -n +2 | awk -F'\\t' '{print $1, $2}' | sort | uniq -c; kill -0 37757"
    result: "read 19:24:07Z: 21 completed success, 4 completed skipped, 1 completed failure = ci-authority/codex/merge-queue-pilot check run 114540615313; log line 54 'ALL_CONCLUDED #7870 head=839bd6a1b065959b90e48d3171edbbe85f4f74f3 at 19:22:18Z total=26' after tick 26 (pending=0), rows 21 success / 4 skipped / 1 failure, read 19:22:56Z; kill -0 37757: no such process; consumed on #7870 as comment 6112888232"
unverified: []
unresolved:
  - "Gate (4) Source Continuity: SUBSTITUTE_SUPERSEDED_NEEDS_NEW_AT_839bd6a1; the acc72f3f substitute covers acc72f3f only; the release-head re-run with all five legs of the DSC is owed and the non-seat ruling on it is owed."
  - "Gate (5) ceiling raises templates/index.html 5_800 -> 5_801 -> 5_827 and scripts/build_free_content.py 5_600 -> 5_602: RECORDED by the seat, NOT accepted by the CI-contract owner; headroom is zero on both probes at 1eb871d6."
  - "The post-#8250 merge of main into #7870 (the three engine/company_intelligence/issuer_profiles.py hunks and the sec_edgar.source_route combined-limit wording) is still owed after #8250 lands; #8250 itself waits on its own gate (4) ruling and on Executive-connector custody, which needs an OAuth the session cannot start."
  - "Executive OS and Linear MCP connectors are unauthenticated in this session; the Subagent Fabric is UNAVAILABLE; no fabric labor was used."
next_actions:
  - "#7870 CI is GREEN at 839bd6a1 on every gating check (consumed, #7870 comment 6112888232); no CI action is open on this head and green is not release. The post-#8250 merge of main will be a new head: exactly one v2 watcher, one non-author READ_ONLY delta read and a fresh five-leg census run at that head before any release DECISION."
  - "Request, never rule, the two non-seat items on #7870 in one note if not already answered: the gate (4) substitute at the release head under the DSC's five legs, and gate (5) acceptance of the two recorded raises by the CI-contract owner (or curation of the three carrier jobs instead of a raise)."
  - "Then #8250 lands first on its own four conditions; #7870 merges main once more (issuer_profiles.py three hunks, sec_edgar wording), its resolution is read against each parent, the census is re-run with all five legs, and ONE release DECISION follows in DEC:FABLE-SEAT order."
do_not_redo:
  - "Do not accept either ceiling raise on the seat's own authority and do not merge #7870 on green alone; both raises stay RECORDED_NOT_ACCEPTED until the CI-contract owner accepts them by cited id."
  - "Do not re-run the per-side packing measurement for 1eb871d6; it is recorded in #7870 comment 6111839715 and showed identical selection on all four sides. Re-measure only after another base-sync."
  - "Do not trust a CI watcher's ALL_CONCLUDED before ci-plan has completed and the ci-pack matrix has registered (about two minutes after push); the 17:14:12Z conclusion at 1eb871d6 is void."
  - "Do not rebase or force-push #7870; every base-sync is a merge of origin/main into the branch, read against each parent."
  - "Do not re-diagnose the 1eb871d6 red: it is union-only (job absent on main; reach via app.main -> app.prophet_observations -> site/turn_watch/turn_watch.json) and repaired by the one-line widening; after every future base-sync run tests/test_ci_pack.py -k test_curated_exclusive_scopes_cover_their_own_import_closure locally before pushing."
danger_areas:
  - "tests/test_ci_pack.py PACKING_PROBES rows are a CI contract with zero headroom at 1eb871d6: any further main-side closure growth in the seven union jobs goes red on the probe before anything else, and the only honest answers are curation or an accepted raise."
  - "The merge-queue pilot check (ci-authority/codex/merge-queue-pilot) fails on every head and is not a gate (#7870 comment 6107602010)."
  - "engine/theme_graph/store.py (#7462) and templates/basket_detail.html.j2 (#7669) stay frozen on this carrier; no product code rides #7870 beyond its approved scope."
---

## Narrative

Two base-syncs in one day because origin/main kept extending the same seven exclusive-scope
jobs that #7870 extends. Each merge was resolved as a union and read by a non-author READ_ONLY
reviewer against each parent; the reviewer's one substantive objection (that "identical
selection on every side" was inferred, not measured) was answered by running each side's own
packer on its own manifest, which is the shape every future base-sync should reuse. The raises
that the unions forced are the real cost: they are recorded, documented per side, and not the
seat's to accept.

The watcher trap is the operational lesson: a check-run list read one second after push shows
only the authority checks, and a watcher that treats "nothing pending" as "all concluded" lies.
The v2 guard (require a completed ci-plan and, when it succeeded, at least one registered pack)
is the rule for every watcher bound by this seat from now on.

The red at 1eb871d6 is the second lesson: a union of two correct closure lists can still be
incomplete, because main-side code reached through the carrier's imports can name a data file
neither parent listed. The closure test catches it in four to eight minutes locally; running it
before every base-sync push is cheaper than a hosted red. The repair (839bd6a1) is the tool's own
prescribed widening and nothing else.
