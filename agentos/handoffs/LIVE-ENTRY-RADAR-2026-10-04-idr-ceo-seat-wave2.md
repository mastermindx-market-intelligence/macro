---
workstream: WS:LIVE-ENTRY-RADAR
session: claude/idr-records-2-20261004
model: fable
ended_because: ci_handoff
prs: [8440, 7274, 808, 797, 8439]
decisions: ["DEC:ENTRY-RADAR-EPISODES-ARE-ADDITIVE-IN-THE-LIVE-PAYLOAD"]
mission: >
  Fable CEO seat for Intraday Dislocation + Reclaim (Chairman handoff on mastermind-terminal issue 784),
  wave 2 of 2026-10-04: publish live Radar episodes to the Terminal, land the reviewed R1-B study
  runner on its carrier, repair the Terminal screen PR's CI red, and pin every fact a cold stranger
  needs to run the registered R1-B v4 study exactly once.
state_before: >
  Records PR 8439 merged at 258af3fa9790. The live payload (entry_radar.live/v1) carried no episodes,
  so the Terminal /dislocations screen (PR 808) could only read fixtures. The S5 runner repair sat on
  ubuntu1 branch claude/idr-s5-r1b-runner-repair-20261004 at 13caccc4cd7c, unreviewed and not on the
  R1-B carrier. Terminal PR 808 was red on an unknown check; PR 797 was behind master. The location
  of the accepted D0 capture (the study's --input-dir/--manifest) was not recorded anywhere in the repo.
changed:
- path: agentos/decisions/DEC-ENTRY-RADAR-EPISODES-ARE-ADDITIVE-IN-THE-LIVE-PAYLOAD.md
  what: >
    Rules that live episodes are an additive top-level `episodes` array inside entry_radar.json
    (plus health.episodes_count / episodes_schema), key absent on the failure path, no second served file.
- path: agentos/handoffs/LIVE-ENTRY-RADAR-2026-10-04-idr-ceo-seat-wave2.md
  what: This record.
verified:
- claim: Producer branch publishes episodes per the frozen spec F1-F5 with tests EP1-EP6
  command: >
    ssh ubuntu1 'cd ~/lanes/wt/idr-producer && git diff --stat 258af3fa9790..d58bcbe13dbe &&
    python -m pytest -p no:cacheprovider -q tests/test_entry_radar_w4_liveness.py
    tests/test_entry_radar_w4_pit.py tests/test_entry_radar_w4_live.py tests/test_freshness_sentinel.py
    tests/test_entry_radar_w4_ledger.py'
  result: >
    live_eval.py +38/-3, test_entry_radar_w4_liveness.py +168; 422 passed in 15.92s (lane baseline
    416); the only caller of _payload is run_pass (grep of engine/ scripts/ tests/ app/). PR 8440 opened,
    armed merge-on-green last, watcher on head d58bcbe13dbeb652e209dd877c791f6fc9b1b8f5.
- claim: S5 runner head is a fast-forward of the R1-B carrier and the frozen surface is byte-unchanged
  command: >
    ssh ubuntu1 'cd ~/lanes/wt/idr-r1b && git merge-base --is-ancestor 3ec5c388de2e 13caccc4cd7c &&
    git diff 3ec5c388de2e..13caccc4cd7c --stat -- research/species/tti_r1b/ data/trial_ledger.jsonl lib/ engine/'
  result: >
    FF_OK, 11 commits, empty frozen-surface diff; outcome-blind review lane IDR_S5_R2B_REVIEW returned
    ACCEPT (BLOCKER 0 / MAJOR 0 / MINOR 1). Pushed non-force onto
    claude/terminal-tactical-r1b-prereg-20260917-sol-005 (PR 7274 head now 13caccc4cd7c); one carrier
    comment issuecomment-5983953299. PR 7274 stays DRAFT / HOLD-FOR-SOL, unarmed.
- claim: Terminal PR 808's red was the plain-language guard, not vitest or tsc
  command: >
    gh api repos/mastermindx-market-intelligence/mastermind-terminal/actions/runs/37229113301/jobs;
    ssh ubuntu1 'cd ~/lanes/wt/idr-t-screen && git diff --unified=0 origin/master -- :/terminal > /tmp/pl.diff &&
    cd terminal && node scripts/check_plain_language.mjs --mode enforce-added --diff-file /tmp/pl.diff'
  result: >
    Failed step "Plain-language guard (forward-only, added lines block)": raw ep.state interpolation and
    three English-only labels in DislocationsView.tsx:532-537. After the fix (TECH [en, zh] table +
    episodeStateLabel() in lib/plainLabels.ts): guard rc=0, npx tsc --noEmit rc=0, vitest
    components/dislocations 17 passed. Pushed as bac7830af2e74997511878f33e9f0e43d97b01a9; watcher re-armed.
- claim: The accepted D0 capture is on the m2studio Mac and its hashes match the R1-A receipts
  command: >
    shasum -a 256 /Users/chriswong/agent-evidence/terminal-tactical-d0-20260917-sol-002/pilot-static-inventory.json
    /Users/chriswong/agent-evidence/terminal-tactical-d0-20260917-sol-002/inputs/AMD.5m.json
  result: >
    59c50ed405bd76c0... == R1-A input manifest sha; bfca1068cd03f182... == RESULT.json input_receipts.AMD.
    Copied to ubuntu1 ~/lanes/d0/terminal-tactical-d0-20260917-sol-002/ (22 symbol files, hashes re-verified).
- claim: R1-B study pre-input admission passes at the reviewed head
  command: >
    ssh ubuntu1 'cd ~/lanes/wt/idr-r1b && python scripts/research/terminal_tactical_r1b_study.py --verify-only'
  result: >
    rc=0; config/prereg/grid/registered-rows sha256 match REGISTRATION_RECEIPT_V4.json; ledger 1823 lines,
    prefix matches; study_cells 60; market_data_read false; outcomes_computed false; no attempt receipt on ubuntu1.
unverified:
- claim: PR 8440 merges green and the VPS payload gains `episodes` after the next live pass
  what_would_verify: >
    Watcher exit CONCLUDED_GREEN / ALREADY_MERGED, blob compare of live_eval.py against origin/main, then
    `ssh root@146.190.142.17 python3 -c "import json; d=json.load(open('/var/lib/macro-live/public/live/entry_radar.json')); print(d['health'].get('episodes_count'), len(d.get('episodes', [])))"`.
- claim: Terminal PR 808 goes green on bac7830a and the deployed /dislocations renders live episodes
  what_would_verify: >
    Watcher exit, deploy `bash /opt/terminal/terminal-build.sh --target-sha <master head>`, anonymous GET
    https://app.mastermind-x.com/dislocations (never sign in).
- claim: The registered R1-B v4 study produces RESULT_V4.json from this head
  what_would_verify: >
    junit receipt at 13caccc4cd7c (suite name = code sha), then ONE run with --input-dir/--manifest/
    --terminal-root ~/lanes/wt/terminal_c0f36cb/--output-dir/--code-sha/--junit; outputs committed onto
    the carrier with the attempt receipt disclosed.
unresolved:
- 'PR 7274 remains DRAFT / HOLD-FOR-SOL: Sol releases; the seat never arms or merges it.'
- 'R2b MINOR: terminal_tactical_r1b_study.py _blob_oid_at_tree lacks its own _object_local guard; fix only together with a re-review, never mid-study.'
- 'Terminal PR 797 head 50bcb5b33e5c0f51dcfc5be58a318fcc8f656879 after update-branch; checks pending.'
- 'Wave 2 of the producer (catalyst attach into episodes) is specified only in notes; it starts after PR 8440 merges.'
next_actions:
- 'Judge the junit receipt (~/lanes/d0/receipts/junit_13caccc4.xml on ubuntu1, suite name 13caccc4cd7c...); then run the study ONCE from ~/lanes/wt/idr-r1b with --attempt-root left at the passwd-home default and --output-dir ~/lanes/d0/receipts/run_13caccc4.'
- 'Commit RESULT_V4.json, TTI_R1B_V4_REPORT.md and the receipts onto claude/terminal-tactical-r1b-prereg-20260917-sol-005 with the attempt receipt path disclosed in one PR 7274 comment.'
- 'On PR 8440 merge: VPS proof of `episodes` in entry_radar.json; then commission producer wave 2 (EpisodeCatalyst mapping from CatalystContext, 900 s source staleness).'
- 'On PR 808 green: deploy with --target-sha and GET /dislocations anonymously; post crops to the PR.'
do_not_redo:
- 'Never re-register R1-B v4, never edit research/species/tti_r1b/* or TTI_R1B_PREREG.md, never run the study a second time on a host whose attempt ledger holds an outcome receipt.'
- 'Never re-post START/ACK on terminal issue 784; never take over LER-C1 PR 6625 (EXACT_HUMAN_GATE on its own carrier).'
- 'Do not rebuild the episodes payload as a separate served file (DEC:ENTRY-RADAR-EPISODES-ARE-ADDITIVE-IN-THE-LIVE-PAYLOAD).'
- 'Do not re-run the memoized S5 test stage experiment: memoization measured 10x net-negative and was removed in 13caccc4cd7c.'
danger_areas:
- 'A study run that dies after the outcome stage leaves outcome_values_persisted null and blocks the study id until Sol authorises a new one; run verify-only and the junit receipt first, then exactly one run.'
- 'Terminal CI typechecks and tests the merge ref; the plain-language guard scans ADDED lines against HEAD^1, so a local tsc+vitest green does not prove a green shard.'
- 'A push to a held PR changes the head Sol will review; always re-read the carrier (comments, reviews, body hold text) in the same cycle and post one comment naming the head.'
- 'The m2studio Mac holds the only on-disk copy of the licensed D0 capture outside Git plus the ubuntu1 copy; never commit it.'
---

Cold-stranger pickup order: memory program file (seat a0115103 addenda), this record, DEC above,
then PR 8440 / 7274 / 808 / 797 state on GitHub. Watchers are session-local scratch processes and die
with the seat; re-arm on the exact heads named above.
