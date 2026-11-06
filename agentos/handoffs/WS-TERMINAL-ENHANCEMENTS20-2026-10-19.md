---
workstream: "WS:TERMINAL-ENHANCEMENTS20"
session: "claude/ssd-terminal-feature-upgrades-e68368 (Fable 5.1 principal seat, Opus 5.5 from 2026-10-18 to 2026-10-20; working files under /Volumes/Mastermind/agent-workspaces/claude/5600d31ffa29643a/e20-seat)"
model: fable
ended_because: complete
mission: >
  Deliver the 20 Terminal feature upgrades E01-E20 end to end through the Terminal delivery
  chain (PR, CI, merge-on-green squash, git-gated terminal-build.sh deploy with --target-sha,
  live verification on app.mastermind-x.com) and close with a per-AC report on Terminal
  issue 916. This checkpoint closes the program after landing trains 5 and 6, the E07 solo
  landing and the release-preflight repair.
state_before: >
  Trains 1-3 and E05 were merged, deployed and live (train 3 PR 960, squash 98b9e664a).
  E07 PR 954 had merged at 3816d3926 but its deploy stopped at gate 0 on a missing
  allowance for the git-ignored scan bundle that train 3's build installs. The E16
  review-rows follow-up, the E17 byte-limit finding and the merge-on-green held-run fix
  were open PRs. mastermindx-2's E12 and E17 slow-connection recovery proposals on issue
  916 were unbuilt, and E11 AC-03 (restatement lineage) was partial because the vendor
  feed has no as-filed history.
changed:
  - path: "Terminal PR 1053 (squash 3e0be25bf)"
    what: >
      Release-preflight allowance for scripts/dist/gen_fundamental_scan.mjs plus a regression
      test that every scripts/dist file the build or nightly names is a staged, installed
      bundle with exactly that allowance. Shipped through the documented first-adoption path
      (DSC:BUILD-WRITTEN-IGNORED-FILE-REFUSES-NEXT-TERMINAL-DEPLOY-AT-GATE-ZERO); E07 went live
      with it.
  - path: "Terminal PR 1069, landing train 5 (squash e8a25a202)"
    what: >
      #1052 E16 review-rows palette step, #1060 E17 dry-run body limit counted in UTF-8 bytes,
      #989 merge-on-green controller fix (the controller's branch refresh no longer leaves a
      held action_required run; #971 closed as superseded). Deployed 2026-10-19T09:59:38Z.
  - path: "Terminal PR 1074, landing train 6 (squash d943b0c12)"
    what: >
      #1071 E12 transcript-archive requests with a named 15 s deadline and an honest
      fallback; #1067 E11-03 statement columns stamped with their SEC filing from EDGAR
      companyfacts by ingest/annotate_sec_lineage.py (run by nightly_fund.sh after
      gen_fund_us.py, warn-and-continue), recasts marked restated; #1073 E17
      duration-independent dry-run recovery (Cancel settles at once, eligibility in the
      request identity, idle reset, the input-change cleanup releases only its own
      request, no client deadline or retry). Merged 2026-10-20T06:33Z; this seat did not run its deploy: the squash is contained in the production release 683eea62b (#1178, built 2026-10-25), read from the live wire marker on 2026-10-31.
  - path: "Macro agentos records (this PR)"
    what: >
      WS-TERMINAL-ENHANCEMENTS20 waves and status refreshed; new DECs for the e2e shard
      split and the one ref-counted page-scroll lock; new DSCs for the gate-0 ignored-file
      refusal, the Massive vX sunset, SEC companyfacts keeping every filing of a period, the
      held controller refresh run, the e2e cap cancel with no failed test, the L01-A02
      checker dropping writes after a .then callback and Playwright rewriting tracked proof
      PNGs.
verified:
  - claim: "Train 5 is live: unauthenticated and oversize dry-run POSTs answer 401, and the E16 review-rows probe passes."
    command: "production read-only probes after deploy.sh wait; exact invocations are transcribed in the CEO_LEDGER 10:15Z entry (e20-seat/status/CEO_LEDGER.md)"
    result: "401 / 401; E16f probe PASS, 48 checks at 1440x900, 820x1180, 390x844 in EN and ZH, no writes, no page errors; it failed on the pre-deploy build"
  - claim: "The E17 recovery fixes four defects and each test can fail."
    command: "cd terminal && npx vitest run lib/__tests__/alertDryRunCancelAndEligibility.test.tsx (at ef9fe8f56, then with master's panel, fd58f9b10 and five mutants swapped in)"
    result: "22 pass; master's panel 14 fail / 8 pass; fd58f9b10 fails only the 2 race tests; mutants fail 4 / 7 / 6 / 3 / 2"
  - claim: "The E17 cancel journey needs the panel to settle Cancel itself."
    command: "npx playwright test e2e/alerts-dry-run.spec.ts (desktop, tablet, mobile projects; fetch wrapped so the first POST ignores its signal)"
    result: "33 pass at ef9fe8f56; with master's panel the journey fails 6/6, state stays running"
  - claim: "The train 6 head passes the affected gates."
    command: "typegen + tsc --noEmit; eslint on the 8 changed TS/TSX files; vitest run lib/__tests__/alertDryRun lib/__tests__/transcript; cd ingest && python3 -c 'import annotate_sec_lineage'; pytest tests/test_sec_lineage.py; bash -n ops/nightly_fund.sh"
    result: "clean / clean / 7 files 123 passed / import OK / 54 passed / clean"
  - claim: "Train 6 merged green and its squash is inside the live release."
    command: "gh pr view 1074 --json state,mergedAt,mergeCommit; git merge-base --is-ancestor d943b0c12 683eea62b (the data-dpl-id marker read from https://app.mastermind-x.com/terminal on 2026-10-31T04:13Z)"
    result: "MERGED 2026-10-20T06:33:30Z, squash d943b0c12; ancestor of the live marker 683eea62b (#1178, 2026-10-25); #1071, #1067 and #1073 closed pointing at the squash on 2026-10-31"
  - claim: "E11 AC-03 is stamped on production after the nightly ran #1067."
    command: "read-only probe of /data/<SYM>.fund.json for GE AAPL MSFT NVDA AMZN JPM XOM KO META GOOGL on 2026-10-31T04:14Z; m1 ~/.cache/mastermind/sec_lineage/last_receipt.json"
    result: "RESULT PASS: 8/10 name sec_companyfacts, 63 columns stamped with aligned periods, 2 restated; JPM and XOM unstamped by design; receipt 3,236 files annotated, 456 fetched, 0 fetch errors, no deadline hit (nightly of 2026-10-30); the same probe failed 0/10 on 2026-10-20 before the run"
  - claim: "The E17 negative-access path is live."
    command: "unauthenticated POST /api/alerts/dry-run on production, 2026-10-31"
    result: "401"
unverified:
  - claim: "E12 transcript-deadline fallback and E17 Cancel/eligibility recovery behave live at 1440x900, 820x1180 and 390x844 in EN and ZH."
    what_would_verify: "a read-only guest probe of the transcript compare route with a stalled ticker index, and a signed-in dry-run Cancel on production; this seat ran neither after train 6 shipped inside release 683eea62b"
  - claim: "E07 AC-03 signed-in two-device sync on production."
    what_would_verify: "an operator signs in on two devices and saves a template on one; the seat never signs in, and the two-context fixture e2e passes"
unresolved:
  - "E13 AC-06 stays partial behind a human-only rights gate: TICKER_NEWS_RAIL is dark and Macro answers 503 without a rights receipt."
  - "E14 AC-02 stays partial by design: the production producer publishes date-only next_date and the spec forbids a new earnings producer; the exact-instant path is unit-proven only."
  - "E07 AC-03 production two-device leg is an operator step (see unverified)."
  - "E15 AC-06 and E18 AC-06 are partial: the local proofs use fixture contracts and a fake alerts API; a signed-in entitled operator closes each on production."
  - "Held PRs #1009 (draft) and #1022 also touch AlertDryRunPanel.tsx and will need a small rebase on the request-identity line when their holds lift; a note is on each. They belong to mastermindx-2 and were not modified."
  - "Two non-blocking review notes in ChartPanel.tsx (dead chartRef guard near :8828; unused imports SuiteRenderBundle and mfBuyShare) are left for the next lane that touches those lines."
  - "The fund nightly may still have a second writer on M2 (spawned task chip task_181dd4fc); not program scope."
  - "SEC lineage leaves JPM and XOM unstamped by design: bank revenue has no comparable SEC anchor and XOM's ticker maps to a 2026 holding-company CIK with one filing; widening coverage is a spawned task chip (task_46184a4f), not program scope."
  - "Production fund.json carries no next earnings date for MSFT, GOOGL, META, KO, JPM and XOM although they report within about two weeks, so the watchlist event planner lists them outside the agenda; a spawned task chip (task_c6c59755) covers it, not program scope."
  - "Production fundamentals have no deep statement history: the vendor endpoint the backfill used was shut off on 2026-10-09 and the nightly never ran the backfill; restoring it is a spawned task chip (task_8e39fb1d), not program scope."
  - "mastermindx-2 reported (issue 916 comment 6283048846) that FundamentalScreen.tsx keeps a stale threshold draft when a different saved screen selects the same field, with a candidate diff and tests proven locally only; it is a spawned task chip (task_c8c9c8a4), not adopted by this program."
next_actions:
  - "Nothing is pending for the program. Later owner-support receipts and proposals from mastermindx-2 on issue 916 (2026-10-30: E14 real-cache retry, E13 editorial-view x catch-up, three unapplied E15 return-navigation proposals) are information for a follow-up lane, not program scope."
  - "If an operator wants E07 AC-03 closed: sign in on two devices, save a study template on one and confirm it appears on the other; record the result on issue 916."
  - "If a news rights receipt is granted, E13 AC-06 can be proven by enabling TICKER_NEWS_RAIL through its existing gate; nothing else is pending for E13."
do_not_redo:
  - "Do not rebuild E12 or E17 recovery; #1071 and #1073 landed on train 6 (squash d943b0c12) and are inside the live release. The E17 client deadline was deliberately not adopted (the duration-independent variant was chosen)."
  - "Do not re-run the E17 mutants or the master-panel falsifiers; results are in PR 1073 and its audit-resolution comment 6264999583."
  - "Do not look for as-filed history in Massive vX financials (410 since 2026-10-09) or v1 (one row per period); SEC companyfacts is the lineage source."
  - "Do not raise the e2e shard timeout; split the shard (DEC:TERMINAL-E2E-SHARD-AT-CAP-SPLITS-NEVER-RAISES)."
  - "Do not merge through an admin bypass, mark an unmerged PR merged, force-push a lane branch or hand-edit an evidence hash."
danger_areas:
  - "A build step that writes a git-ignored file into /opt/terminal/terminal needs a release-preflight allowance in the same PR, or the NEXT deploy stops at gate 0 (DSC:BUILD-WRITTEN-IGNORED-FILE-REFUSES-NEXT-TERMINAL-DEPLOY-AT-GATE-ZERO)."
  - "ingest/ emitters run as scripts; verify with cd ingest && python3 -c 'import <mod>', never pytest alone."
  - "React 19 can commit new inputs and handle a click before the old inputs' passive cleanup runs; an effect cleanup must release only state it owns."
  - "A Turbopack dev server can wedge at 0% CPU on a compile; stop only your own server, remove terminal/.next/dev and restart on fresh ports."
prs: [1053, 1069, 1052, 1060, 989, 971, 1074, 1071, 1067, 1073, 954]
decisions:
  - "DEC:TERMINAL-E20-LANDING-TRAINS-ONE-CI-ONE-SQUASH"
  - "DEC:TERMINAL-E2E-SHARD-AT-CAP-SPLITS-NEVER-RAISES"
  - "DEC:TERMINAL-PAGE-SCROLL-LOCK-IS-ONE-REF-COUNTED-LOCK"
discoveries:
  - "DSC:BUILD-WRITTEN-IGNORED-FILE-REFUSES-NEXT-TERMINAL-DEPLOY-AT-GATE-ZERO"
  - "DSC:MASSIVE-VX-FINANCIALS-SUNSET-LEAVES-NO-AS-FILED-HISTORY"
  - "DSC:SEC-COMPANYFACTS-KEEPS-EVERY-FILING-OF-A-PERIOD"
  - "DSC:TERMINAL-L01A02-CHECKER-DROPS-WRITES-AFTER-A-THEN-CALLBACK"
---

## Frontier at this checkpoint

All twenty upgrades are merged and deployed. Five landing trains (numbered 1-3, 5 and 6;
no PR was opened as train 4), the E05 and E07 solo
landings and the release-preflight repair #1053 carried them; the per-AC report is on
Terminal issue 916 (https://github.com/mastermindx-market-intelligence/mastermind-terminal/issues/916#issuecomment-6538904273).

Train 6 (PR 1074, squash d943b0c12) merged on 2026-10-20T06:33Z while this seat was away; another release (#1178, 683eea62b, 2026-10-25) carried it live, so no deploy was run from this seat. E11 AC-03 moved to pass on the 2026-10-31 production probe. E15 AC-06 and E18 AC-06 were re-marked partial after the independent report review because their local proofs run on fixture contracts and a fake alerts API; each closes with a signed-in entitled operator on production.

The remaining partial rows are bounded by things the seat may not do: a news rights
receipt (E13), a producer the spec forbids (E14 exact instants) and signed-in production
sessions (E07 two-device, E15 real contracts, E18 bulk readback). Each is recorded with
what would close it.
