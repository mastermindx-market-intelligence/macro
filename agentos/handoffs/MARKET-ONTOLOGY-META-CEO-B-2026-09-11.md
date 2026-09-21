---
workstream: WS:MARKET-OS
session: |
  harness session d640f3ef-1305-4b6c-aa5d-2d6d5e3dc515 (Claude 5 runtime, Fable), holder of the
  Meta-CEO B seat since 2026-09-08 21:1xZ; bound on macro#6819 with issuecomment-5592587864 (the
  ACK issuecomment-5557271957 and the Wave 1 comment issuecomment-5577816742 are never repeated).
  The Wave 2 comment on macro#6819 is issuecomment-5626381233 and is never repeated either; this
  wave's single Wave 3 comment on macro#6819 is issuecomment-5630979484 (posted by the seat
  2026-09-11 07:3xZ) and is never repeated.
model: fable
ended_because: complete
mission: >
  Wave 3 checkpoint for Meta-CEO B (Chairman override of 2026-09-05/06; charter
  research/MARKET_ONTOLOGY_META_CEO_CHARTER_2026_09_06.md). Half B is F06 F07 F08 F09 F11 F12
  F13 plus the Supabase migration namespace, the identity/tenant contracts and the A-spare
  packets. This record covers 2026-09-11 02:00Z to 07:15Z - the settings-and-teams cascade
  landing on Terminal master, the production DDL chain 0019 to 0021 and its ledger flip, the
  rulings that unblocked each of them, and the state of every open half-B PR at the boundary.
  It is written so a cold successor on any account can resume from GitHub plus this file plus
  the durable kit.
state_before: >
  The Wave 2 record (agentos/handoffs/MARKET-ONTOLOGY-META-CEO-B-2026-09-10.md) closed at
  2026-09-10 22:35Z with Terminal master at 8872328a4, production still serving ee320e39 because
  the nested deploy stage from #561 had not been installed on the box, and the DDL queue stopped
  at 0018. Between that boundary and this one the box script was installed by hand, #561, #564,
  #553 and #546 landed with proved on-master deploys, and the seat went into the operating split
  the Chairman set at 22:16Z 2026-09-10: Fable keeps rulings, ratifications, merges, DDL and
  records; every mechanical step goes to a one-shot Opus orchestrator with a full brief. Wave 3
  opens one minute after Terminal #548 merged as bad423f5, with migrations 0019, 0020 and 0021
  on or riding to master and none of them applied.
changed:
  - path: agentos/handoffs/MARKET-ONTOLOGY-META-CEO-B-2026-09-11.md
    what: "This Wave 3 checkpoint record. Records only; no source or product effect."
verified:
  - claim: "Six Terminal PRs merged in this window, each by its own merge-on-green plus auto-merge at a head the seat had ratified: #548 bad423f5 at 02:00:51Z, #566 e43733c1 at 02:47:50Z, #554 7e15e502 at 03:30:44Z, #556 19c57aca at 04:13:26Z, #550 3cdcd746 at 05:42:28Z and #568 2b7d3485 at 07:04:11Z."
    command: "the merged-PR sweep and the armed watcher reported each merge; terminal_reviews/_post_merge.sh <pr> then read the merge commit and the served build"
    result: "Master moved bad423f5 to e43733c1 to 7e15e502 to 19c57aca to 3cdcd746 to 2b7d3485. Ratification ids: #566 issuecomment-5628427199; #554 extension issuecomment-5628556084 at 89801c918 with the merge-only refresh to c0bac733 proved in issuecomment-5628790545; #556 extension issuecomment-5629182033; #550 issuecomment-5628217615 then 5628842864 then 5629236178 then 5629868043 as its head moved; #568 issuecomment-5630295484 extended by 5630524745. #548 merged at the extension head aa8344ee, whose orchestrator fact comment is 5628012190."
  - claim: "Every one of those merges except the last was proved live: the served data-dpl-id equals the merge commit."
    command: "terminal_reviews/_post_merge.sh <pr>, which builds on the box and reads the served data-dpl-id"
    result: "bad423f529d8460bbc83c67f92199ae4ff1b3163 after #548 (the fifth consecutive on-master deploy), e43733c1f3b0c8a9f35c44876948ff9ab8cb474a after #566, 7e15e502338e34d16ac120f56f4d4ddc7123469a after #554, 19c57aca3569ae938dc420b4c4860116de492208 after #556 and 3cdcd746b86d478ff139dd5fea408b66fce065af after #550 - eight consecutive on-master deploys. #568's chain was still running at the boundary."
  - claim: "Migrations 0019, 0020 and 0021 are applied in production, in ledger order, from master's own copies."
    command: "python3 ddl/raw_apply.py <file>.sql receipt_00NN.json <label> - SQL read from origin/master, Management API raw fallback, pre and post readbacks, every read masked"
    result: "0019_team_role_changes at 05:58:15Z, 0020_team_ownership_transfer at 05:58:34Z, 0021_resource_grants at 05:59:15Z, all apply_status 201. Post-readbacks show team_role_changes with its index and row-level security on with seven policies, four functions and two triggers; transfer_team_ownership present as a security-definer function with EXECUTE for the authenticated role; resource_grants with three indexes, row-level security on, seven policies, three functions, one trigger and the grant helpers. Receipts are ddl/receipt_0019.json, receipt_0020.json and receipt_0021.json with copies in records_queue/ddl_receipts/; none carries a project reference or a token shape. Receipt comments: issuecomment-5630176327 on #550 for 0019 and 0020, issuecomment-5630176531 on #548 for 0021."
  - claim: "The ledger on master now records 0019 and 0020 as merged in 3cdcd746 and all three as applied on 2026-09-11, with every pin moved in the same PR."
    command: "Terminal #568 (branch claude/mo-b-ledger-0019-0021-applied); python3 -m pytest tests/test_supabase_migration_namespace.py -q in strict and default modes; single-worker vitest on the migration contract tests; cd terminal && npx tsc --noEmit"
    result: "Six files, +74/-54: RESERVATIONS.json rows, the pytest namespace snapshot asserts, the resource-grants contract test, the README application and reservation tables and their prose, and the 0019/0020 header lines; the stale 0017/0018 comment was corrected in passing. 86 passed, 1 skipped in both pytest modes; 49 vitest tests over 4 files; tsc exit 0. Merged as 2b7d3485."
  - claim: "A squash merge orphaned the b-f12-9 evidence pointer and broke the unit shard for every open Terminal PR, and the fix landed on #568."
    command: "read the failing job for #567 at d8946ff6 (f12_9TeamOwnershipTransferEvidence.test.ts:160) and reproduce in a worktree at master 3cdcd746"
    result: "#550's pointer named 2f775a39, a commit on the PR branch; the squash merge left it out of master's history, and with fetch-depth 2 in ci.yml the guard's ancestry walk could not reach it, so the same single test failed on #567 and on #568 (5353 passed, 1 failed). The seat moved the pointer to the squash commit 3cdcd746 on #568's own branch (bde87941 to 9f0b4cce, EVIDENCE.yml only, all five pinned hashes unchanged, no crop recaptured, 24 passed) rather than opening a standalone fix PR, which would have deadlocked on its own namespace red until #568 landed."
  - claim: "#550's merge of master could not be resolved by restamping, because both sides had recaptured the same settings rail and the merged rail matched neither."
    command: "git merge origin/master in the #550 worktree; read the conflicting crops and the two capture headers"
    result: "35 conflicts: one README, four EVIDENCE.yml, three settings code files and 27 binary crops. #550 had recaptured at 4d5520d9 for the Accuracy and Team rows; #548 had recaptured so the rail showed Accuracy and Sharing; the merged rail is eleven rows and neither side's crops depict it. The seat ruled a recapture at the merge commit (see the rulings section); 54 crops were recaptured across four packets, one script at a time."
  - claim: "The mobile end-to-end red that sat on #550 for two heads is a contention flake, not a fault in the change."
    command: "a read-only Opus investigation of crosshair-price-label.spec.ts, ChartPanel.tsx, hoverTagPaint.ts and playwright.config.ts, plus three data points from CI"
    result: "The spec's two-step pointer move at :285-286 omits pricePaneTop and :290 is the one unhardened one-shot bounding-box read, while every sibling assertion polls a settled sample; the hover tag keeps its text when hidden, so the text assertion passes on an invisible tag; the three retries run on one correlated machine; the config records a 15 to 25 per cent pointer-spec failure rate at peak. Nothing in #550 executes on the chart route. The same shard passed on #566, #554 and #548 at the same master, failed 3 of 3 on two #550 heads, then passed at 6ae7585e when #550 merged. Hardening shipped as Terminal #567 (test-only), ratified issuecomment-5629184599."
  - claim: "Every refresh of an armed head in this window was proved merge-only before it was accepted, and every hand-resolved merge was type-checked."
    command: "md5 of the sorted plus/minus lines of git diff origin/master...<sha>, equal file counts, git merge-base --is-ancestor; then cd terminal && npx next typegen && npx tsc --noEmit"
    result: "#554 89801c918 to c0bac733 (md5 e80b1d82, 28 files both sides) and #567 through 0ca68d37 to 1df1e60f to d8946ff6 (md5 0ddb0e3a, one file) all verified with a fact comment: 5628790545, 5629593209 and 5630118210. Type-check exit 0 on every hand-resolved merge and every restamp push on #554, #550, #556, #567 and #569."
  - claim: "A full-tree bidirectional lock screen ran after every master move and never let an asserted lock row through stale."
    command: "the scratchpad wt_lockcheck.py over every packet in terminal/docs/pr-crops at each refreshed or merged head"
    result: "Zero asserted mismatches at every head this wave, across 22 to 24 packets as new ones arrived. The same 14 non-asserted rows stayed stale throughout and are recorded as an open item; the b-f12-5 trailing-text exception was left intact everywhere."
  - claim: "macro #7032's stale change-request was disposed of by the seat, and the PR is armed and approved."
    command: "gh pr view 7032 once per fact from Stream M; the disposition posted as issuecomment-5629120534"
    result: "mastermindx-2 requested changes at 43dc98fb on 2026-09-10 22:46:24Z and never answered the re-review request from 00:01Z; MastermindX1 approved the ratified head 807ca8ba at 03:32:25Z, which does not clear another reviewer's block. The seat dismissed review 5172990438 with reasons, set merge-on-green, and the review decision became APPROVED. The PR still merges only on its own green."
  - claim: "No macro PR of this seat merged in the window; the three-runner pool is the reason."
    command: "the macro armed-list watcher plus one gh read per red from Stream M runs 5 to 8"
    result: "#7021's pack-4 and #7010's pack-3 reds are the known suite-labels pair that #7032 heals (two failed, the unknown token presence:quantity_vs_quality and TREAT_AS_UNSETTLED against WATCH_BOUNDARY), and their ci-gate reds are derivative. #7008's pack-6 red sits on run 34530823515, queued since 2026-09-10T21:12Z and unreadable while queued - runner starvation, not a code fault. The only macro merges seen were foreign: #7016 at 03:57:30Z and #7068 at 05:16Z."
unverified:
  - claim: "#568's post-merge chain completes: the served data-dpl-id equals 2b7d3485, #567 refreshes merge-only onto it and goes green, and #569 refreshes by taking master's EVIDENCE.yml while keeping its test change."
    what_would_verify: "terminal_reviews/_post_merge.sh 568 printing a served data-dpl-id equal to master, then the merge-only proof on #567 and a green unit shard on both."
  - claim: "macro #7032 concludes green and merges, and the update-branch round it unblocks turns #7020, #7003, #6905, #6958, #6909, #7012, #7021, #7010 and #7006 green."
    what_would_verify: "gh pr view 7032 MERGED, then a refreshed head on each with the suite-labels pack reds gone."
  - claim: "macro #6920 merges at 8ad66422 and #7007 can then be retargeted to main, re-checked over its thirteen files, marked ready and armed."
    what_would_verify: "the #6920 watcher reporting MERGED, then a three-dot diff on #7007 against origin/main showing the same thirteen files."
unresolved:
  - "#568's post-merge chain was still running at the boundary: the deploy proof, the #567 merge-only refresh and the #569 refresh are all owed. At 07:15Z the armed watcher reads #569 4176cd7e DIRTY and #567 d8946ff6 BEHIND with the pre-#568 failure still attached."
  - "Terminal #569 (the guard that deepens the fetch once before failing an ancestry check, plus the same pointer move #568 carried) is ratified and armed but not merged; until it lands, a future squash of a carrier whose packet walks ancestry breaks the unit shard again the same way."
  - "The b-f12-b5-3 account-completeness crops are four rail rows stale on master: they were captured when the rail had seven rows and it now renders eleven. The packet pins no wrapper, so nothing fires. The lane is specified in records_queue/specs/T-PL-CROP-1_settings_rail_crop_rot.md: add the SettingsPanel.tsx and SettingsProvider.tsx pins, then recapture the eight crops at the then-master."
  - "Fourteen non-asserted lock rows are stale on master (b-f08-6 six rows, b-f12-b5-1 two, b-f12-b5-2 one, the three PL-6 batches five). They have no evidence test, so nothing fires; the same lane that adds the wrapper pins should restamp or retire them with header disclosures."
  - "Ledger pin parity: only the 0017 and 0021 prefixes have a vitest contract test that reads RESERVATIONS.json; 0018, 0019, 0020, 0022 and 0023 are pinned by the pytest snapshot alone. Also 0017's merged_sha sits in a different key position from every other merged row, the applied 0019/0020/0021 files still carry their packet-era do-not-apply banners, and terminal/e2e/tools/capture_f12_9_team_ownership_transfer.cjs still prints PR #557 on its ledger-row header while the ledger says 550. All of it is specified in records_queue/specs/T-LEDGER-PIN-1_vitest_ledger_pin_parity.md as one docs-and-tests PR."
  - "macro #7032 has been armed and approved since 03:44Z with its packs still churning; the update-branch round on #7020, #7003, #6905, #6958, #6909, #7012, #7021, #7010 and #7006 waits on it. #6920 is armed and #7007 waits on it."
  - "macro #7008's pack-6 red cannot be read while its run stays queued, so the red is classified binding but its assertion is not quotable."
  - "Terminal #496 is foreign and on hold, dirty against master, untouched all wave."
  - "The two plain-language sweeps from Wave 2 are still specified and not started: records_queue/specs/T-PL-NI-1_ni_sweep.md and records_queue/specs/T-PL-LOCK-1_i18n_lock_rows.md, the second now with a Wave 3 addendum."
next_actions:
  - "Finish #568's post-merge chain: prove the served data-dpl-id equals 2b7d3485, refresh #567 merge-only and post its note, then refresh #569 by taking master's EVIDENCE.yml and keeping only its test change; let both merge on green."
  - "Post exactly ONE Wave 3 comment on macro#6819 naming this record, and paste its issuecomment id into this file's session field. Never re-ACK, never repeat the Wave 1 or Wave 2 comment."
  - "When macro #7032 merges, run the update-branch round on the nine PRs behind it and prove each refreshed head merge-only before accepting it."
  - "When macro #6920 merges, refresh #7007 onto main, re-check its thirteen files, mark it ready and arm it."
  - "Open the b-f12-b5-3 lane (wrapper pins plus an eight-crop recapture at master) and the ledger-pin parity lane; both are specified and both are one PR each."
  - "Keep applying the squash law on every carrier that lands a packet with an ancestry guard: the post-merge chain checks the pointer against master's history in the same run and files the fix immediately."
do_not_redo:
  - "Do not re-review any head named in a ratification comment. Ratified or extended this wave: Terminal #548 aa8344ee, #550 e5bd65fe, a954bc47, 837e4653 and 6ae7585e, #554 89801c918 and c0bac733, #556 19fb9084, #566 2a659a19, #567 0ca68d37, #568 bde87941 and 9f0b4cce, #569 4176cd7e."
  - "Do not re-apply 0019, 0020 or 0021. The receipts of record are issuecomment-5630176327 on terminal#550 for 0019 and 0020 and issuecomment-5630176531 on terminal#548 for 0021, with receipt files in the kit's ddl/ and records_queue/ddl_receipts/."
  - "Do not point a packet's capturedAtHead at a PR-branch commit once the PR has squash-merged; master's history does not contain it and the depth-2 checkout cannot reach it. Point it at the squash commit."
  - "Do not open a standalone fix PR for a defect that only clears when a flip lands: its own namespace test will be red until then. Put the fix on the flip's branch as a ratification extension."
  - "Do not rerun a concluded CI run to clear a bot-made refresh. Look for a run held as action_required and have the seat approve it."
  - "Do not call the crosshair mobile shard a code fault on #550: it is a documented contention flake with three data points, and #567 is the hardening."
  - "Do not resolve a crop conflict by keeping either side when both sides recaptured the same surface: neither depicts the merged surface. Recapture at the merge commit under a seat ruling."
  - "Do not end an orchestrator turn while waiting for a watcher event. Wait in a foreground blocking loop; a turn that returns before handling the event is a failed run."
  - "Do not re-ACK or re-bind on macro#6819, and do not post a second Wave 1 or Wave 2 comment."
danger_areas:
  - "A squash merge silently invalidates any evidence pointer that names a PR-branch commit, and GitHub's depth-2 checkout hides the cause: the whole open queue fails one unit test at once, with the failure looking like a fault in each innocent PR."
  - "A migration merge reddens every armed head on the namespace test until its ledger flip lands, and the flip is itself red until it carries every pin the carrier shipped."
  - "A byte-level evidence lock is blind to a shared container: a packet whose crops frame an overlay or panel wrapper rots silently as the wrapper gains rows, because the lock pins no file that changes."
  - "Two branches that recapture the same shared surface for different reasons produce a merge no restamp can make truthful; only a recapture at the merge commit can."
  - "When the merge-on-green bot refreshes a carrier itself, the resulting run can sit as action_required while the PR shows blocked with every present check green - it looks like a hung queue and is a missing approval."
  - "The macro ci-linux pool is three runners: a pack can stay queued for nine hours, its logs unreadable, and a red on such a run says nothing about the code."
  - "End-to-end pointer specs on the mobile shard fail 15 to 25 per cent at peak load, and all three retries share one machine, so a real flake looks like a hard 3-of-3 failure."
prs:
  - 6819
  - 6920
  - 7007
  - 7008
  - 7010
  - 7021
  - 7032
  - 548
  - 550
  - 554
  - 556
  - 566
  - 567
  - 568
  - 569
decisions:
  - "DEC:SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06"
  - "DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06"
discoveries:
  - "DSC:PR-CI-ONLY-RUNS-AGAINST-MAIN-BASE"
  - "DSC:SHARED-CLONE-PACK-STORM-STALLS-THE-FLEET"
---

# Meta-CEO B — Wave 3 checkpoint (2026-09-11 02:00Z to 07:15Z)

Seat: harness session d640f3ef, model Fable, sole owner of half B for the whole window.

Authority: the Chairman override of 2026-09-05/06 and the operating split set at 22:16Z on
2026-09-10 — Fable turns are for rulings, ratifications, merges, production DDL and records, and
every mechanical step around a decision goes to a one-shot Opus orchestrator with a full brief,
because a brief cannot be amended once the agent is running. Watchers report events only; nothing
polls GitHub on a short cycle.

This wave is the settings-and-teams cascade landing. Six Terminal PRs merged in five hours, three
production migrations were applied in ledger order, and the wave ends with the ledger flipped on
master. Nothing merged on macro: the three-runner pool kept every armed PR pending.

## What landed

Terminal, on master, in order:

- **#548** B-F12-B5-1 explicit grants, carrying migration 0021 — merged **bad423f5** at 02:00:51Z
  at the extension head aa8344ee, one minute into the window.
- **#566** the ledger flip for 0021, the seat's own PR, opened 02:12:18Z — merged **e43733c1** at
  02:47:50Z. Ratified issuecomment-5628427199. Four files: the reservation row, the README tables,
  the missing namespace snapshot assert and a new contract test, because #548 shipped none.
- **#554** B-F13-6 claim authoring form — merged **7e15e502** at 03:30:44Z. It needed a hand
  resolution first: three evidence locks had each restamped the shared lexicon to their own
  pre-merge value and the merged lexicon hashes to a third, so one row per packet moved,
  hash-only, with the disclosure in header lines.
- **#556** B-F13-7 first resolver and last close — merged **19c57aca** at 04:13:26Z. Its 24 add-add
  conflicts were all stale copies of the stack it was built on; every one took master's bytes.
- **#550** B-F12-8 team roles, carrying migrations 0019 and 0020 — merged **3cdcd746** at
  05:42:28Z after four ratified heads, two of them produced by hand merges and one by a
  54-crop recapture.
- **#568** the applied flip for 0019, 0020 and 0021, carrying the b-f12-9 pointer repair — merged
  **2b7d3485** at 07:04:11Z, which is this record's boundary.

Every merge except the last was proved live in the same chain that caught it: the served
data-dpl-id equalled the merge commit each time, eight consecutive on-master deploys by the end
of #550. The deploy fault that ran through Wave 2 is gone; the Vercel checks still read failure on
every PR and are still the free-tier build rate limit, not code, and are not required.

macro merged nothing of this seat's. #7032 is armed and approved, #6920 is armed, and both have
had their packs churning for hours behind a three-runner pool. The only macro merges the sweep saw
were foreign: #7016 at 03:57:30Z and #7068, a China Risk Radar hotfix, at 05:16Z.

## Production DDL

After #550 landed, the seat applied, in ledger order and from master's copies, through the
Management API raw fallback with pre and post readbacks and every read masked:

- **0019_team_role_changes** at 05:58:15Z — the change log table with its index, row-level security
  on, seven policies, four functions and two triggers. Pre-image empty.
- **0020_team_ownership_transfer** at 05:58:34Z — the transfer function as security definer with
  EXECUTE for the authenticated role.
- **0021_resource_grants** at 05:59:15Z — the grants table with three indexes, row-level security
  on, seven policies, three functions, one trigger and the watchlist read paths. The readback
  helper printed one spurious missing-object token, which is the known regex artefact of the
  parser reading a conditional; the readback itself is complete.

Receipts are in the kit at ddl/receipt_0019.json, receipt_0020.json and receipt_0021.json with
copies in records_queue/ddl_receipts/, and they carry no project reference. Receipt comments:
issuecomment-5630176327 on #550 for 0019 and 0020, issuecomment-5630176531 on #548 for 0021.

Then one flip PR, #568, moved all of it at once: the two reservation rows to merged in 3cdcd746,
all three to applied on 2026-09-11, the pytest namespace asserts, the resource-grants contract
test and the README tables and prose. That is the Wave 2 law held: a flip carries every pin.

With 0021 applied the chain 0014 through 0021 is complete. 0022 and 0023 are on master and stay
unapplied until the seat runs them in ledger order.

## The squash that broke the queue

At 06:29Z #567 went red on a test nobody had touched: the b-f12-9 ownership-transfer evidence
guard reported that its capturedAtHead was not an ancestor of HEAD. The pointer named 2f775a39,
a merge commit on #550's branch, which was correct while #550 was open and became unreachable the
moment #550 squash-merged as 3cdcd746. GitHub checks out pull requests at depth 2, so the guard's
ancestry walk could not reach it and the same single test failed on every open Terminal PR
(#568 included), with 5353 other tests passing.

The seat's ruling has two halves. The pointer must name a commit in master's own history, so it
moved to the squash commit 3cdcd746, with the five pinned hashes unchanged and no crop recaptured.
And because a standalone fix PR would have been red on its own namespace test until the flip
landed, the pointer fix went onto #568's branch as a ratification extension (bde87941 to
9f0b4cce) and rode in with the flip. The guard's own hardening — one deepening fetch before it
gives up — is Terminal #569, ratified and armed, which refreshes onto master after #568.

This is the third distinct shape of the same depth-2 problem this seat has met, after the
merge-commit form and the pre-restamp-tip form. All three are now written into the kit's common
law, and the design lesson is recorded as an addendum to M-EVIDENCE-GATE-1.

## Rulings this wave

- **Recapture at the merge commit.** #550's merge of master carried 27 conflicting crops because
  #550 and #548 had each recaptured the same settings rail for their own reason, and the merged
  rail is eleven rows that neither side depicts. The standing law says report, do not recapture;
  that law assumes one side is still true. The seat ruled a recapture of the 27 plus #550's own
  two packets, 54 crops across four capture scripts run one at a time, at the merge commit, so
  that the merge commit is both the capture head and the recapture commit's parent and the
  ancestry guard holds. It also fixed the merged rail order: account, team, accuracy, billing,
  usage, preferences, alert delivery, terminal, sync, webhooks, sharing.
- **Review disposition on macro #7032.** A change request from mastermindx-2 sat on a head three
  revisions stale from 22:46Z the previous day; a re-review request from 00:01Z went unanswered
  and MastermindX1 approved the ratified head at 03:32:25Z, which does not clear another
  reviewer's block. The seat dismissed the stale review with reasons, posted the disposition as
  issuecomment-5629120534 and set merge-on-green. The PR still merges only on its own green.
- **The mobile hover red is a flake.** Three data points settled it: the same shard green on
  #566, #554 and #548 at the same master, 3 of 3 failures on two #550 heads, then a pass at the
  head that merged. The investigation named the mechanism — an unhardened one-shot bounding-box
  read, a hover tag that keeps its text when hidden, three retries on one correlated machine —
  and the hardening shipped as #567 rather than as a change to the carrier.
- **Bot-refresh approvals.** When the merge-on-green bot refreshes a carrier itself, the resulting
  run can sit held as action_required while the PR reads blocked with every present check green.
  Orchestrators report it; only the seat approves it; nobody reruns a concluded run.
- **The waiting rule.** An orchestrator that armed a background monitor and ended its turn waiting
  was stopped and relaunched: waiting happens in a foreground blocking loop over the watcher
  files, and a run that returns before handling its event is a failed run.
- **The commit gate accepts a skip.** The gate now matches a passed count optionally followed by a
  skipped and a warnings count, because the namespace suite has one conditional skip; a line
  containing failed still blocks the commit.

## Open half-B state at 07:15Z 2026-09-11

| Repo | PR | Head | State | Next act |
|---|---|---|---|---|
| terminal | #568 applied flip 0019-0021 | MERGED 2b7d3485 07:04:11Z | landed at the extended head 9f0b4cce, carrying the b-f12-9 pointer repair | finish the post-merge chain: prove the served data-dpl-id equals master |
| terminal | #567 e2e hover hardening | d8946ff6 | ratified, armed, BEHIND with the pre-#568 failure attached | merge-only refresh onto 2b7d3485, then merge on green |
| terminal | #569 f12-9 guard deepen | 4176cd7e | ratified, armed, DIRTY | refresh taking master's EVIDENCE.yml and keeping only the test change, then merge on green |
| terminal | #496 | f664ba3d | foreign, dirty, on hold | not this seat's; leave alone |
| macro | #7032 suite-labels heal | 807ca8ba | armed, review decision APPROVED after the disposition, packs still pending | merge on its own green, then the update-branch round |
| macro | #7020 #7003 #6905 #6958 #6909 #7012 #7021 #7010 #7006 | see each PR | ratified; the pack reds are the suite-labels pair #7032 heals | update-branch after #7032, prove each refresh merge-only, merge on green |
| macro | #6920 F06 ticker identity panel | 8ad66422 | ratified, armed | merge on green |
| macro | #7007 | b2a3eb17 | ratified, draft on #6920's branch | after #6920: refresh, retarget to main, re-check thirteen files, ready, arm |
| macro | #7008 | 3ef72d55 | ratified, armed; pack-6 red on a run queued since 21:12Z the previous day | wait for the runner; the red is not quotable while the run is queued |

## Laws this wave minted

- **A pointer dies with its branch.** After any squash merge of a carrier whose packet walks
  ancestry, the pointer must be moved on master to the squash commit in the same post-merge run,
  or every downstream PR fails the unit shard.
- **An ancestry guard must deepen before it fails.** Depth-2 is a checkout default, not a fact
  about history; one deepening fetch and a retry turns a fatal red into a correct check.
- **When both sides of a merge recaptured the same surface, recapture at the merge commit.** The
  report-do-not-recapture default assumes one side is still truthful.
- **A packet that frames a wrapper must pin the wrapper.** A byte lock over the packet's own files
  cannot see the rail above it gaining rows, so the crops rot with nothing firing.
- **Put a fix where it can go green.** A standalone PR for a defect that only clears when another
  PR lands is a deadlock; extend the ratification of the PR that clears it.
- **Approve, never rerun.** A bot-made refresh can leave its run held for approval; rerunning a
  concluded run destroys evidence and fixes nothing.
- **Wait in the foreground.** A one-shot orchestrator has no resumption, so it must not end a turn
  before handling the event it was launched to handle.

## Operating pattern at the end of the wave

Fourteen orchestrator runs carried this wave. Stream T ran runs 7 through 15: post-merge chains
and deploy proofs for #548, #566, #554, #556, #550 and #568, the hand merge of #554, the
preparation of #556 for retargeting, the merge-only verification of #567 twice, the hand merge
of #550 onto #556's master, the 0019 and 0020 readback preparation, and the classification of the
pointer break with a verified patch it deliberately did not push. Run 8 was stopped for waiting in
the background, which is where the waiting rule came from. Stream M ran runs 5 through 8, all of
them classification: the approval that did not clear a block, the suite-labels pair on #7021
and #7010, and the starved pack-6 run on #7008. Three auxiliary agents worked #550 under a lease —
one that stopped and reported 35 conflicts rather than guess, one that merged and recaptured 54
crops, one that merged again and moved the pointer. A read-only investigator produced the flake
verdict. Fixers produced #567 and #569, and flip agents produced #566 and #568.

Every one of them returned facts and left the decisions to the seat, which is the pattern the
Chairman set: the seat ratified eleven heads in five hours, applied three migrations, and never
merged past a real red.

Plain language stays a program law: no machine text in anything a customer reads, and Chinese copy
uses 你 and never the formal second person. The two sweeps that finish that job are still specified and still waiting for
the settings cascade to finish landing, which is now one refresh away.
