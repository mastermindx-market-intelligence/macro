# Market-Intelligence Institutional Buildout — continuation handoff 2026-10-12 (W10)

Successor of research/MARKET_INTELLIGENCE_BUILDOUT_CONTINUATION_HANDOFF_2026-10-11.md (W8 and W9).
Workstream record: agentos/workstreams/WS-MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT.md (W10 wave).
Handoff record: agentos/handoffs/WS-MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT-2026-10-12.md.
Wave B design inputs, frozen: research/product_intelligence_local_delivery/WAVE_B_NEWS_FLOW_RAIL_SPEC_2026-10-12.md
and research/product_intelligence_local_delivery/WAVE_B_SEAT_RULINGS_2026-10-12.md.
A cold stranger can resume from this file alone. Read section 2 (what is running and who owns it),
section 3 (what is decided), section 7 (what to do next), and only then section 8.

## 0. Identity and mandate

- Seat: Meta-CEO session fd47d431 (Claude Code, Claude Opus 5.5).
  - SSD worktree: /Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/mi-g10-seat-20261012b-65328750a32333f2.
  - Records branch: claude/mi-w10-records-20261012b.
  - Retired trees, never touch: the 10-12 wiring tree mi-g10-wire-20261012-f81b47649825c6d8 and the locked
    records tree mi-w10-records-20261012-604b8a87ae4f997d.
- Program: Mastermind PR #1258 MERGED. It is the owner-preserving integration overlay of umbrella issue
  mastermindx-market-intelligence/mastermind#1202. Op key: market-intelligence-institutional-buildout-20261004.
- Mandate, unchanged from 10-11: resume instead of getting blocked, take ownership, and finish end to end.
  Orchestrate through Opus 5.5 sub-orchestrators that drive fabric lanes. Limitations for the Chairman
  come LAST.
- Chairman rulings of 10-12, in order:
  1. "Assess what is left in the Marketin Intelligence program, how we. can improve it and upgrade it
     extensively even more", to be done with a wide Grok fan-out. Ruling 2 supersedes the fan-out.
  2. "Okay Grok has refreshed the usage pool so we don't need to rush to use it now. Revert back to
     normal subagent fabric orchestration."
- Topology now has three levels:
  - The seat.
  - At most two Opus 5.5 orchestrators (orchestrator agent type, fable-mode skill, no native children).
  - Fabric lanes run through the B-kit remote_sub launcher, in tier order: GLM first, MiniMax for
    mechanical work, Cursor last.
- Orchestrators return DRAFT PRs plus exact heads. Only the seat:
  - marks ready, labels, and edits PR bodies;
  - wires CI job files;
  - merges and posts on carriers;
  - accepts by artifact.

## 1. Wave plan and exit gates

- W8 and W9 (10-11) are closed: see sections 1 to 4 of the 10-11 file. Nothing there is re-opened here.
- W10 is the G10 lane wave plus the Wave B news-flow rail. The G10 lanes:
  - news store, news velocity, news ops, annotation, catch-up gap, cluster false positives;
  - universe diagnosis, company theme exposure health;
  - leadership receipt edge matrix, verdict preservation edge matrix;
  - terminal client matrix, terminal company-theme card tests, terminal rail accessibility.
- Exit gate for every lane:
  1. Squash-merged on concluded checks with a head pin.
  2. Blob-identical on main, by per-path comparison after a bare fetch.
  3. PRODUCTION_PROOF at the rung the lane can reach:
     - app code served by macro-api or macro-ticker-news on the VPS: the deploy rung;
     - site output: the render rung;
     - test-only lanes: stop at MERGED plus LANDED, because nothing ships.
- Wave B exit gate:
  - B1 (store plus velocity), B2 (flow API, flow_compare.v1) and B3 (terminal strip) merge in that order.
  - B2 is live on the VPS before B3 merges.
  - The strip renders the DARK theme live and always shows known_at. LIGHT exists only as a specimen
    (ruling D-W1).
- Wave B is design-frozen. The two Wave B files named in the header are the contract source.
  - ORCH-WB writes the lane-facing contract (wb_news_flow_contract.md in the seat scratchpad, about 31 KB
    at 10:46Z).
  - Thawing it after B1 or B2 has launched restarts both lanes.
- B4 belongs to ORCH-RV2, not to Wave B's merge chain. It covers:
  - B4-macro: macro PR #8982, leadership receipt hardening;
  - B4-terminal: a follow-up after terminal PR #970.

## 2. Lane matrix (state at 11:50Z on 10-12)

Merged on macro main (squash, UTC; full rows and proof receipts in section 4):
- l-receipt-matrix #8967 (08:48:58Z), n-velo #8902 (09:05:12Z), n-uni #8896 (09:10:56Z), n-annot #8897
  (09:42:08Z), CI scope widening #8960 (10:14:58Z), cte-health #8894 (10:16:24Z), n-gap #8898
  (10:17:06Z), n-clu #8905 (10:17:27Z), n-ops #8900 (10:55:14Z), n-store #8895 (11:01:15Z), n-matrix
  #8903 (11:33:59Z), B4-macro #8982 (11:35:03Z), U7 v-registry-matrix #8993 (11:44:25Z).
- n-velo has no production consumer until Wave B B1 and B2. n-uni reaches its production rung at the next
  successful nightly that runs its builder, which is gated on the runner broker (section 8). B4-macro's
  PRODUCTION_PROOF waits on the covering render (section 4).

Merged on terminal master:
- t-client-matrix #968: 5161a621, 10:32:00Z. Keeps the newest ticker-news snapshot across refresh races
  and restores state unavailable (AC-E13-01). LANDED by blob comparison. PRODUCTION_PROOF is still owed:
  the VPS terminal unit last started at 03:46:23Z, before the merge (section 7).

Open on terminal master, owned by the seat, merged by hand on concluded checks:
- t-cte-card-tests #970, head bda2f3dfa7ab. Its tablet e2e shard was cancelled at the 60-minute cap at
  11:34:51Z. One rerun of the failed jobs started at 11:41Z and a watcher is armed. Its merge releases
  B4-terminal.
- t-rail-a11y #974, head 7dd04008da89. Tablet and mobile were cancelled at the cap at about 11:34:20Z.
  One rerun of the failed jobs started at 11:41Z and a watcher is armed. Its merge releases Wave B B3.
- Neither PR touches e2e, and the shards run on hosted runners, so the cancels are runtime variance near
  the cap. If a rerun caps again, the terminal lane freezes until E20's shard split (#963) lands on master.
  Never touch #963 or #960.

Wave B news-flow rail (ORCH-WB). DRAFT PRs pass to seat custody once judged and reviewed:
- B1 store and velocity #8998, branch claude/mi-g10-wb-store, head 0fbe5e460c6e. Judged PASS by
  artifact. Its review lane was refused at admission at 11:39Z (ubuntu0 host temperature at or above
  the limit, rc 75, no lane started) and retries after a cool-down. Seat steps once the review concludes:
  wire the new store tests into job ticker-news-qbus, make one body edit, ready it and merge on concluded
  checks.
- B2 API #8995, branch claude/mi-g10-wb-api, head 18d7a9a9a3ab. Judged PASS with one defect (D8). Its
  review lane was admitted at 11:37Z. B2 integration (lane mi-g10-wb-api-int-r0) is gated on
  "B1 MERGED". The B2 body carries the seat's own "do not merge before B1" sequencing note. It is not a
  Sol hold, and it is removed in the single body edit after B1 merges.
- B3 terminal is gated on "#974 MERGED" (ubuntu3, disk gate).

In flight under ORCH-RV2, no PR yet:
- verdict_preservation defect lane: released at 11:4xZ by the seat message "#8993 MERGED c91b297d". It
  owns engine/verdict_preservation.py (the UnicodeDecodeError paths at :144-145 and :159-160) and
  flips the two strict xfails in tests/test_verdict_preservation_edge_matrix.py.
- B4-terminal: gated on the seat message "970 MERGED".
- ticker_news defect lane: serialized after B2 merges, because B2 owns app/ticker_news.py. It fixes the
  404 decoded-slash bypass of _private_error (route at app/ticker_news.py:438, helper at :70) and the
  422 responses that lack the private headers (:405-406, 441-442, 553), and flips #8903's two strict
  xfails.

Deferred:
- i-matrix #8899 (DRAFT, flag stays off) and i-leg-readiness, until C19 PR #8943 lands. Never touch
  C19 work.

Orchestrators (Opus 5.5; resume by message, never re-spawn):
- ORCH-RV2, repair wave round 2: F (n-matrix, merged), U7 (merged), B4-macro (merged), B4-terminal and
  the two defect lanes.
- ORCH-WB, Wave B news-flow rail: B1, B2, B3.
- Their ledgers live in the seat scratchpad. It is session-local; the facts that matter are copied into
  this file.
- Ended and never to be resumed: ORCH-F, ORCH-N, ORCH-OPS, ORCH-D, ORCH-RV, ORCH-UP.

## 3. Decided (binding; reopen only on a material invalidator)

Chairman and seat:
- Fabric ruling of 10-12 (Chairman ruling 2 in section 0). The Grok fan-out is over and normal fabric
  orchestration is back: at most two Opus 5.5 orchestrators, each driving lanes through the B-kit
  remote_sub launcher, GLM first, MiniMax for mechanical work, Cursor last. Orchestrators spawn no
  native children. Only the seat marks ready, labels, edits PR bodies, wires CI job files, merges,
  posts on carriers and accepts by artifact.
- Terminal #968 root cause. The first version of the PR turned a failed background refresh into an
  interrupted flag (setLiveInterrupted true) and kept the old rows on screen. That broke the accepted
  rule AC-E13-01, which master pins in newsCatchupPanel.test.tsx line 187 with the copy "News is
  temporarily unavailable". Ruling: a failed refresh restores the unavailable state, and every race fix
  stays. Evidence: on the unfixed hook 6 of the 9 race tests failed (out-of-order refresh, refresh
  failure 503, restricted refresh 401, initial snapshot for a different ticker, EventSource reconnect,
  writes after unmount). After the fix, 9 of 9 passed, and 44 of 44 across the five news test files.
- n-uni #8896 repair is done: commit 1c6aeb0c restores min_count 1 parity. DO_NOT_REDO.
- Runner broker. DSC:M2-RUNNER-LISTENER-SELF-CANCELS-ITS-JOB-AFTER-TEN-BROKER-POLL-FAILURES (recorded
  10-11 in W9-7, PR #8868) stands. Once ten broker long-polls fail in a row, an M2 listener cancels any
  job that has run past about 95 minutes. The nightly has been gated on this since 10-09. Never
  re-investigate it. The host network suspects are an operator act (section 8).
- GH001 belongs to Sol (#8042 and #8756): the claims ledger file is over the push size limit. This
  program never touches it.
- The four defects pinned by strict xfails are owned by this workstream and are real:
  - engine/verdict_preservation.py lines 144-145: _pin_ok catches only OSError around its utf-8
    read_text, so a non-UTF-8 source raises UnicodeDecodeError.
  - engine/verdict_preservation.py lines 159-160: build catches only OSError and JSONDecodeError, so a
    non-UTF-8 registry raises.
  - app/ticker_news.py: the decoded-slash 404 bypasses _private_error (lines 438 and 70).
  - app/ticker_news.py: the query-bound 422s carry no private headers (lines 405-406, 441-442, 553).
  - The verdict pins live in U7 #8993 and the ticker-news pins in n-matrix #8903. A fix PR must flip
    its xfail markers in the same PR, so it branches only after the PR holding its pins merges
    (section 7).

Wave B seat rulings (full text in WAVE_B_SEAT_RULINGS_2026-10-12.md):
- D-W1 theme. The strip ships DARK live. LIGHT exists only as a specimen, which a test generates by
  server-rendering the live NewsFlowStrip and NewsFlowTally components with the fixture props. Light
  CSS lives only in the specimen's own stylesheet and never reaches runtime CSS, so
  tickerNewsRailMount.test.ts line 47 stays green. The PR body labels cells L1 to L6 as SPECIMEN.
- D-W2 comparison thresholds: flow_compare.v1 as written. The thresholds are named module constants.
  The comparison is display-only and never feeds ranking, sizing or gating. Any threshold change bumps
  the rule id. It uses the exact median, and display shows at most one decimal (a median of 2.5
  renders as 2.5, never 3).
- D-W3 SSE: flow stays off SSE. The terminal never increments or recomputes flow from SSE frames; the
  engine is the only counter. The strip always shows known_at, so an aged count is labeled rather than
  hidden. Live ticking is a product-law question outside Wave B.
- O1, ruled 11:2xZ. A response with no flow key leaves the strip hidden and the rest of the panel
  unchanged. Spec goal G4 and spec section 3.1 govern, and a missing flow key never forces the panel
  into the unavailable state. Line 63 of the rulings file was corrected to say so. This is not a thaw:
  the frozen lane contract already followed G4.

ORCH-RV2 decisions (repair wave round 2):
- D1. Run ids use the prefix mi-g10-rv2-, then the lane, then the round. Never reuse the mi-g10-rv- or
  mi-g10-up- run ids.
- D2. rv_sec_F_rev.md is the review section and rv_sec_F.md is the repair section.
- D3. B4-macro is checked for disjointness at hunk level against Sol's #8639 for
  templates/basket_detail.html.j2, and the same test is run against #7870 and #7669. The tsChip map
  hunk (about lines 654-660) is disjoint, so the lane proceeds.
- D4. The F tree's head equals the stated head. The ubuntu1 tree fast-forwarded from ade3257d to
  c408fa3f.
- D5. The seat took custody of #8903 at 8aa2d39a46b7. No lane pushes to it.

ORCH-WB decisions (Wave B):
- D1. The lane contract wb_news_flow_contract.md was frozen about 10:45Z (541 lines, 31,210 bytes). It
  validated 6 of 6 fixtures and 17 of 17 table rows.
- D2. A thaw restarts B1 and B2. There have been no thaws: #8895's diff changed only the snapshot
  cluster-watermark SQL, so the contract holds.
- D3. Decisions under contract section 9 belong to the orchestrator.
- D4. B1 and B2 run on ubuntu0 with GLM glm-5.3 through remote_sub, launched with /bin/bash. B3 is
  planned for ubuntu3 behind a disk gate.
- D5. B2's tests use the frozen fake. The one exception, test_flow_counts_match_visible_rows_under_rights,
  uses the real store once B1 is MERGED.
- D6. The B2 PR stays DRAFT, and its body carries a sequencing note against merging before B1. The seat
  removes that note in its single body edit after B1 merges and before marking the PR ready. Until then
  the hold scan flags the note. It is the seat's own sequencing note, not a Sol hold.

Commission gates (seat messages that release work):
- "8895 MERGED" released B1. Sent 11:01:15Z with squash d60a2fe6.
- "970 MERGED" releases B4-terminal (ORCH-RV2).
- "974 MERGED" releases B3 (ORCH-WB). The B3 design pin is written first.
- "B1 MERGED" releases the B2 integration step.
- U7 closed J-U7-1 in fast-forward commit c0dc13f6 to 4d70cd26 (+21/-8, owned file only). Both strict
  xfails now name an owner and carry a raises guard. Lane evidence: a RuntimeError probe turns FAILED,
  and mutations M1, M2 and M3 add 1, 10 and 2 red ids. The seat's wiring commit 6f1c0367 sits on top.

## 4. Merges and production proofs (UTC, 10-12)

Macro main, squash-merged by hand on concluded checks with a head pin, each blob-identical on main:

| PR | lane | squash | merged | rung reached |
|---|---|---|---|---|
| #8967 | l-receipt-matrix | 5ff7dacd52ec | 08:48:58Z | MERGED + LANDED (test-only) |
| #8902 | n-velo | 595c91d0590f | 09:05:12Z | MERGED + LANDED (no consumer until Wave B) |
| #8896 | n-uni | 74031a83236f | 09:10:56Z | MERGED + LANDED (nightly rung gated, section 8) |
| #8897 | n-annot | b936b479aa06 | 09:42:08Z | PRODUCTION_PROOF (macro-api) |
| #8960 | CI scope widening | 323b766b6bd5 | 10:14:58Z | CI (later runs compile the scopes) |
| #8894 | cte-health | 0a2569a6c2b8 | 10:16:24Z | MERGED + LANDED (test-only) |
| #8898 | n-gap | ef25c14211d7 | 10:17:06Z | MERGED + LANDED (test-only) |
| #8905 | n-clu | be06bdbc67c1 | 10:17:27Z | PRODUCTION_PROOF (macro-api) |
| #8900 | n-ops | fa3716ec18d7 | 10:55:14Z | MERGED + LANDED, bytes present on the host |
| #8895 | n-store | d60a2fe68129 | 11:01:15Z | PRODUCTION_PROOF (ticker-news writer) |
| #8903 | ticker-news package matrix | 8e44cf297280 | 11:33:59Z | MERGED + LANDED (test-only; its strict xfails flip when the ticker_news defect lane lands) |
| #8982 | B4-macro leadership receipt edges | 624f9000dff7 | 11:35:03Z | MERGED + LANDED; PRODUCTION_PROOF owed after the covering render |
| #8993 | U7 v-registry-matrix | c91b297dda9f | 11:44:25Z | MERGED + LANDED (test-only; wired once in job unrun-factor-research) |

Production proof receipts (read-only on the host):
- #8897 and #8905: the VPS checkout head 735d63b0 contains both, and macro-api restarted at 10:33:16Z
  (pid 3707055 to 3718201).
- #8895: at 11:27Z the VPS checkout head was aba5e3308bd. Its engine/qbus_news_store.py blob is
  969f3b5d, identical to main. macro-ticker-news, the single writer, restarted at 11:03:38Z (pid
  3741813), two minutes after the merge. Its start line reported ok true with count 503, and the journal
  holds zero error-level lines since the restart. macro-api restarted again at 11:09:16Z (pid 3745881)
  on a later main.
- #8900: scripts/ticker_news_inventory.py is on the host with blob 9d4b4a98, identical to main. It is an
  ops report run by hand (docs/ops/ticker-news.md), so its rung stops at bytes present. The seat did not
  run it against the live store.
- #8982: it changes templates/basket_detail.html.j2, so the proof needs a render. Render run 38243588166
  (push at 624f9000) is pending behind run 38219837639 (push at c1a942f3), whose render job waited
  07:49Z to 10:08:52Z for a runner and was still in progress at 11:42Z. The shared lane owns both; never
  cancel or re-run them. The proof target is the live theme-detail invalid chip: "Theme state dated
  after this read" and "主题状态日期晚于本次判读".
- The VPS clone is shallow (is-shallow-repository true). An ancestry check there returns false
  silently. Prove presence by blob comparison, never by merge-base.

Terminal master:
- #968 t-client-matrix, merge 5161a62179e1, 10:32:00Z: MERGED + LANDED. PRODUCTION_PROOF is owed. The
  live .deployment-id is e0c405a09b68 (#962, committed 03:33:49Z), and the 5161a621 to e0c405a0
  comparison reads "behind 3". BUILD_ID is build-TfctsWXpff2fKS (03:46:21Z), and terminal.service has
  been active since 03:46:23Z. The plan is one deploy covering #968, #970 and #974 (section 7).

## 5. Danger areas and guard lessons

Merging and CI:
- Merge by hand on concluded checks only, with the full head pinned. Before each merge, scan the PR's
  title, body and comments for a hold and re-read the head, because a sweeper update-branch can move it.
  Arm last, and never push into an armed PR.
- Body edits: make exactly one, while the PR is still DRAFT. Then mark it ready, then push or
  update-branch. A second body edit cancels the PR's ci-authority run.
- Reds that may be ignored: ci-authority/codex/merge-queue-pilot (a standing inactive context),
  "Workers Builds: macro", and Vercel, including the terminal's "Deployment rate limited". Nothing else.
- Terminal e2e cap. The required check "Terminal typecheck + tests" aggregates terminal-e2e (needs plus
  always), so a tablet or mobile shard cancelled at the 60-minute cap turns it red. The fix belongs to
  E20: #963 splits those shards into halves and lands through E20's train #960. Never push, arm or merge
  #963 or #960. If #970 or #974 goes red only from a cap cancel, one rerun of the failed shards on the
  PR's own run is allowed. That is never a production run.
- Hold-scan false positive: the B2 PR body carries the seat's own sequencing note (section 3, ORCH-WB
  D6). It is not a Sol hold. The seat removes it in its one body edit after B1 merges.

Session guards (Claude Code, this host):
- The isolation guard refuses a directory change chained into a version-control command, unquoted
  variable paths, command substitution inside one, chained or piped version-control commands, the
  run-from-another-directory flag, a sleep chained to a command, and process substitution. Use one plain
  command per call with literal absolute paths. Redirects into and out of files work.
- The CI wait guard refuses a repeat read of the same PR or run within 300 seconds. Background watchers
  own CI reads. A refusal is waited out by working another lane, never evaded.
- A directory change in a plain shell call moved this session's working directory into
  research/product_intelligence_local_delivery. Use absolute paths everywhere.
- Large writes through the file tools time out on this host. Append prose with shell heredocs in chunks
  of about 3 KB.
- Plumbing commit for wiring the CI legacy-jobs file without touching the checkout:
  1. Write the edited file out and store it as a blob with hash-object.
  2. Rebuild three trees with ls-tree, the swap_entry.py helper (exactly one entry swapped) and mktree:
     first the ci tree, then the CI parent directory tree, then the root tree.
  3. Make the commit with commit-tree on the PR head. A merge variant takes two parents.
  4. Check it with a diff stat against the head, and with merge-tree write-tree against main.
  5. Push the commit object to the branch ref.

Host and production (read-only for this program):
- macro-entry-radar-pack.service and macro-sentinel.service were in the failed state on 10-12 while
  their timers stayed active. Never restart them. They are routed to their owners.
- The VPS clone is shallow (section 4).
- Terminal deploy mechanism:
  - The only supported flow is in the terminal repo's DEPLOY.md: branch and commit, PR to master, merge,
    then run the build on the VPS.
  - The command is bash /opt/terminal/terminal-build.sh with --target-sha and the full lowercase 40-hex
    sha. That sha must be contained in freshly fetched, protected origin/master.
  - Its W2A source-receipt gate, made of ops/terminal_release_preflight.py and
    ops/terminal_source_audit.production.json, must be clean for the current generation. It is never
    bypassed.
  - It builds without downtime: an atomic .next swap, with automatic rollback.
  - It syncs runtime code: ingest, scripts, config, contracts, hub and signal_layer. It also installs
    ops/terminal-data as /usr/local/bin/terminal-data and refreshes the build script itself.
  - While it runs it holds /var/lock/macro-update.lock, so the macro three-minute pull skips.
  - The live identity is /opt/terminal/terminal/.deployment-id. Other seats run this script (bc28e47ee54f
    on 10-11 at 18:18:44Z). Check that no build is running before starting one.

## 6. Do not redo (accepted work; reopen only on a material invalidator)

A fresh session, a lost transcript or an absent memory is not a material invalidator.

- Every PR listed as MERGED in section 4 is accepted. Never re-open, re-spec, re-build or re-review it.
  What is still owed is its proof rung, and section 4 names each one.
- ORCH-F, ORCH-N, ORCH-OPS, ORCH-D, ORCH-RV and ORCH-UP have ended. Never re-spawn them. ORCH-RV2
  and ORCH-WB are resumed by message only.
- The update.sh lane-freeze fix #8864 reached PRODUCTION_PROOF on 10-11 at 21:13:16Z. Every
  three-minute tick ends with "deploy finished with status 1 (frozen lanes: w2c)". Disarming the
  options timer on each frozen run is by design, and the earlier W9-5 expectation is retracted.
- The nightly outage root cause is recorded (W9-7 #8868; #8748 comment 6114287529). The M2 runner
  listeners cancel themselves after repeated broker long-poll failures, and GH001 rejects the commit
  tail. Never re-investigate either. The 10-12 nightly proofs stay gated on them.
- The press-feeds 401 is resolved. Do not reopen it.
- Wave B judging is accepted as judged: B1 #8998 PASS, B2 #8995 PASS with defect D8. A fresh session
  reads the review packet and judges only what changed after it. It never re-judges by rebuilding.
- B4-macro #8982 is merged. Only the live chip check is owed (section 4).
- U7 #8993 and n-matrix #8903 are merged. Each is owed only the defect lane that flips its strict
  xfails (section 2).
- The terminal e2e cap cancels on #970 and #974 are runtime variance near the 60-minute cap on hosted
  runners. Neither PR touches e2e. Never debug them in this program: E20 owns the shard split (#963).

## 7. Next actions (in order; each names the event that starts it)

1. Terminal #970 and #974, when a watcher reports concluded checks:
   - Run the hold check and re-read the head.
   - Merge by hand with match-head-commit on the full head.
   - Blob-compare the PR files against master.
   - Then send ORCH-RV2 "970 MERGED <merge sha>", which starts B4-terminal.
   - Then send ORCH-WB "974 MERGED <merge sha>", which releases B3.
   - If a rerun caps out again, freeze the terminal lane until #963 lands and record that here.
2. Terminal deploy, after #970 and #974 merge (or #968 alone if they slip):
   - Check that no build is running.
   - Run the build script with the full master sha (section 5).
   - Verify .deployment-id, which read e0c405a09b68 before this program's terminal merges.
   - Verify the terminal.service restart time.
   - That deploy is the PRODUCTION_PROOF for #968 and #970.
3. B1 #8998, when its review concludes clean:
   - Wire tests/test_qbus_news_flow_store.py, and any new velocity test files, into job
     ticker-news-qbus with the plumbing recipe (section 5).
   - Make one body edit, mark it ready and merge on concluded checks.
   - Verify landing by blob comparison and the wiring count.
   - Then send ORCH-WB "B1 MERGED <squash sha>", which starts B2 integration.
4. B2 #8995, after B2 integration returns and is judged:
   - Make one body edit that also removes the seat's own sequencing note.
   - Wire tests/test_ticker_news_flow_api.py, mark it ready and merge.
   - Live proof: the macro-api restart through the deploy regex, then one request against the new route.
5. After B2 merges:
   - Release the ticker_news defect lane under ORCH-RV2.
   - Confirm B3 is moving if #974 has merged.
6. The verdict_preservation defect lane, when its DRAFT PR returns:
   - Judge it by artifact: red before the fix, green under TZ=UTC and TZ=Asia/Hong_Kong, owned files only.
   - The test file is already wired.
   - Merge on concluded checks.
7. #8982 PRODUCTION_PROOF, when render 38243588166 or a newer covering push render concludes success:
   check the live theme-detail invalid chip text in EN and ZH.
8. Nightly 38192634426, when it concludes:
   - Run the #8864 live proof script.
   - Check #8807, #8816, #8828, data health and GH001.
   - Then post ONE comment on #1202, read forward from counterpart edge 6111762953. The last seat post
     is 6114460481.
9. Deferred: i-matrix #8899 and i-leg-readiness, after C19 #8943 lands.
10. Records:
    - Write the agentos handoff and update the workstream record, then run the agentos validate script.
    - Commit the five named paths, push the records branch, open the PR and merge on concluded checks.

## 8. Chairman blockers (only a human act clears these; listed last on purpose)

- Runner broker:
  - The US nightly 38192634426 has been queued since 01:37Z.
  - One render job waited 2h19m for a runner.
  - The M2 listener self-cancel pattern is recorded in W9-7.
  - The host network suspects (VPN, Little Snitch, Tailscale) are an operator act.
  - Packet loss from the LAN toward the code host is part of the same picture.
- GH001: the nightly commit tail is rejected at push by the size limit (claims.jsonl about 123 MB in
  the nightly tree). Sol owns it on #8042 and #8756.
- MCP authorization:
  - linear-server, mastermind-executive and the figma plugin need OAuth through the claude.ai connector
    settings or the mcp menu.
  - mmx-cimd-probe refuses connections.
- Grok login on mb and m1. Only the operator completes it.
- Data rights and access:
  - Benzinga body and image rights.
  - Massive 403.
  - twitterapi.io 403.
- Rulings the seat does not hold:
  - Package R #8438.
  - ITP GAP-E.
  - C19 F2 to F5.
  - Sol #7711 prereg v2.
  - The PSKY and KHC owner PRs.
  - The identity replay DNR.
  - The signed-in rail check.
- Informational, no act needed: Vercel deployment rate limits, pool saturation, and ubuntu0 thermal
  admission refusals (rc 75; lanes retry after a cool-down).
