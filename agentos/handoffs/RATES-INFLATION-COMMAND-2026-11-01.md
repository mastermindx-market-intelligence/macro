---
workstream: WS:RATES-INFLATION-COMMAND
session: sol/web-cpi-live-repair-20261014-xh01
model: sol
ended_because: ci_handoff
mission: "Repair stale macro Events CPI detection and reduce official-source-to-visible-publication latency within the incumbent release owner."
state_before: "Production retained cpi:2026-10-14 as parser v1 published_unparsed under a fresh heartbeat; the signed-in November calendar showed in 20d for November 5."
changed:
  - path: research/rates_inflation_command/e2e_20261013/MASTERPLAN.md
    what: "Section 18 records the bounded R1/F0/V0/B1/A0 incident work; this remains the only task tree."
  - path: scripts/watch_release_publications.py
    what: "Retained CPI archive/parser upgrade recovery, source pacing and backoff, canonical producer lock, validated atomic public write, intended-candidate hash for failed-public-write healing."
  - path: scripts/vps_live_orchestrator.py
    what: "Dedicated release lane; fast compatibility until its timer is installed; 60-second idle heartbeat; read-only public postcondition with no unsupported writer attribution."
  - path: app/deploy/update.sh
    what: "Idempotent missing/drifted release-unit migration, old fast-service drain plus its existing lane lock, smoke and fail-closed restoration."
  - path: app/deploy/live-setup.sh
    what: "Setup transaction preserves unit bytes and timer intent, drains release ownership, and restores after dedicated or fast smoke failure."
  - path: app/deploy/live-rollback.sh
    what: "Drain all public-directory writers and acquire canonical fast/release locks before withdrawing artifacts."
  - path: templates/release_publications_live.js
    what: "Two-second hot-window visible polling, focus resync, hidden pause, in-flight coalescing and bounded older-snapshot guard; mirrored in site assets."
  - path: research/rates_inflation_command/e2e_20261013/evidence/calendar_freshness_20261101/
    what: "Eight actual Chromium component proofs across themes, languages and desktop/mobile; public-before and isolated verified-recovery evidence with honest scope."
verified:
  - claim: "Original incident is present in the real signed-in Events modal."
    command: "Connected Chrome macroCalendarTab DOM snapshot on www.mastermind-x.com/macro.html, then open Events."
    result: "Historical CPI 08:31 ET extracting banner and November 5 in 20d were visible; no production state mutation performed."
  - claim: "The public endpoint heartbeat does not clear retained CPI extraction failure."
    command: "GET https://www.mastermind-x.com/live/release_publications.json and inspect cpi:2026-10-14."
    result: "HTTP 200/no-store, original detection 2026-10-14T12:31:17.596439+00:00, published_unparsed, parser v1, data_ready false."
  - claim: "Parent client/API candidate and first backend/deploy integration are locally executable."
    command: "python3 -m pytest -q tests/test_vps_live_orchestration.py; python3 -m pytest -q tests/test_official_release_parsers.py tests/test_release_actuals.py tests/test_release_publications_live_client.py tests/test_status_error_leak.py"
    result: "122 orchestration/deployment cases and 100 parser/ledger/client/API cases passed; five existing FastAPI warnings. Current-main integration remains to be verified."
  - claim: "A visible existing Events component reflects verified public bytes without reload."
    command: "python3 research/rates_inflation_command/e2e_20261013/evidence/calendar_freshness_20261101.py"
    result: "Eight nonblank Chromium cases; maximum observed update 1796.11 ms. Controlled local clock/routes, not a natural upstream latency or production proof."
  - claim: "The dated official CPI archive is available from the actual production host."
    command: "Existing watcher _fetch from /opt/macro on 146.190.142.17 with incumbent request headers."
    result: "Archive HTTP 200, 1373525 bytes, 0.251 seconds; RSS 200 in 0.025 seconds. Read-only probe."
  - claim: "Countdown PR #10106 has independent source review and exact-head focused verification."
    command: "Fabric macro-countdown-10106-review-20261101-c2-01; parent pytest tests/test_release_radar_date_selection.py."
    result: "Grok 4.7 non-author PASS at 1ad0a0e45eaae42dc0163d7bccb71470efa983b8, two nonblocking minors, 8 tests passed. Review accepted against SHA256 40360c052d0799334591ee2478ae63179e698634b964bbd7203a8cd6b80017d4. Formal GitHub APPROVED not claimed."
unverified:
  - claim: "The full backend candidate is independently accepted and merged."
    what_would_verify: "Final source tests, independent non-author review at the pushed material head, binding CI, and normal merge readback."
  - claim: "The stale CPI and countdown are repaired in production."
    what_would_verify: "Installed SHA, dedicated timer/service state, canonical CPI verified original identity and timestamps, served asset hash, signed-in real modal and correct New York countdown."
  - claim: "Every future natural release reaches the browser inside the controlled latency target."
    what_would_verify: "Actual source-availability, request, extraction, public-write and browser observations on a natural publication; agency delays and backoff remain separate."
unresolved:
  - "This is a nonterminal recoverable checkpoint. The authorized mission is still active."
  - "#10106 merge-on-green was armed after accepted review and concluded binding checks; remain until merge and signed-in production proof."
  - "#9435 remains unarmed. New backend/setup edits and owned evidence are not yet committed."
  - "Final tests and handoff validation pass; current-main integration, exact material-head review and production release remain."
next_actions:
  - "Reconcile current main into the original candidate, then verify changed integration surfaces; all deployment tests are in the existing CI-enrolled orchestration suite."
  - "Finish controlled latency/failure verification; update this checkpoint and section 18 with actual final results."
  - "Selectively commit owned paths, preserving the two pre-existing untracked files; push original #9435 branch and verify its exact remote SHA."
  - "Obtain independent material-candidate review, conclude binding checks, and use normal merge-on-green release without self-approval/self-merge."
  - "Verify the deployed source/runtime/publication and signed-in Events UI; record remaining natural-release observation separately."
do_not_redo:
  - "Do not open a replacement workstream, PR, task tree, publisher, queue or registry."
  - "Do not repeat the completed paid census/build/review dispatches. Backend proposal response is retained and terminal, not accepted."
  - "Do not infer pre-embargo publication from RSS time. Keep official schedule and period/source checks."
  - "Do not reopen source access or auth; Studio Direct C2 on m2studio and existing VPS key are already authorized and verified."
  - "Do not push #10106 while armed. Read actual merge status and follow the existing disarm protocol if a change becomes essential."
danger_areas:
  - "Preserve unrelated untracked engine/release_publication_analysis.py SHA256 945335cd2a51610f4e7ed9c6bb6038a2bfd9a55fe17debe72fd644dd1faa6f3a and tests/test_release_publication_analysis.py SHA256 46f6426f5f59dd25f0e036dfb1f383e8aba9d8923f36603c16fc3b078035d5f2."
  - "Canonical producer lock must cover state read through final public replacement; no later parent copy or staged unlink."
  - "Do not restore fast ownership while a dedicated writer remains unreconciled. Preserve installed disabled/masked timer intent."
  - "The old fast process may execute its pre-update inode; updater must drain it and hold fast.lock before the dedicated lane starts."
  - "CPI actuals and model projections are different surfaces; fresh heartbeat is not evidence of fresh extraction."
  - "Never print credentials from macro-live.env or API environment files."
prs: [9435, 10106]
---

# Calendar publication repair checkpoint

This dated record preserves ongoing work; it is not a completion or production
acceptance claim. Protected procedure pin is Mastermind
19cb00cfed26b68f0a8a5cdc0f2f1a9463a3feec (Skillpack 1.0.1, bootstrap 1).

Parent committed head before the backend repairs:
7dd3c1fcc64859c12d00cbf96f5e1c19ed2f15db. Its original PR remains #9435.
Countdown PR #10106 exact reviewed head:
1ad0a0e45eaae42dc0163d7bccb71470efa983b8.

Paid backend proposal macro-release-fastpath-build-20261101-c2-01 is terminal
with root macro-release-freshness-20261101-c2. Response SHA256:
9600caf67ae8e7aba2de70bf5cbaaa6324b76a3adbaa6bd747c8a438942433e5.
It was not accepted: it retained a post-lock parent publication copy, allowed
a 240-second idle heartbeat beyond the browser's 180-second freshness limit,
and lacked safe installed-lane rollout restoration. Parent repairs address
those concrete defects and need independent review as a new material candidate.

The original controlled browser proof hash is
7f2e5c6f7fef702446a18039c3222f016a0d65b6d3a1e849046797a321af98c6.
The component fixture deliberately excludes the separate forecast script;
its Loading projections text is not a production countdown claim.
