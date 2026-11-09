---
key: PRESS-WIRE-DISPOSITION-KEEP-AND-FIX-20261108
question: >
  Should macro's marketing-press-wire.yml Actions workflow (cron */5, id 323156104)
  be disabled until the Chairman's X-posting gate opens, or kept running?
answer: >
  Keep the workflow active and running. Do NOT disable. The lane is the only
  continuously-booking press feed (items ob-2026-11-08-bd4069e9e3 et al.) feeding
  the publish queue that the X gate will open onto; disabling it would leave the
  gate opening onto an empty spool. Instead, fix in place: (1) raise the wire
  job's timeout-minutes from 10 to 30 so the ~6-7h-interval runs stop dying at
  the 10-minute wall (18 of last 20 runs cancelled by this exact mechanism,
  steps 1-4 success, step 5 killed mid-poll, dispatch skipped); (2) leave
  MARKETING_PUBLISH_ENABLED as the Chairman's dry-run/publish kill switch,
  untouched; (3) when X posting gate t_fd170576 unblocks, verify
  delivery-readback runs (currently skipped) as the re-arm acceptance probe.
  Re-evaluate this disposition only if the lane again books nothing for 30+
  consecutive completed runs.
rationale: >
  The disable recommendation rested on a stale premise. Fresh sweep 2026-11-08:
  last-20 tally is 18 cancelled / 2 success, not all-cancelled; the two newest
  runs (#1231 19:54Z, #1232 23:24Z) succeeded, booked an item, and dispatched
  marketing-publish (run 42535138274, success). Observed cadence is ~12 runs/day
  (1232 runs over 102 days), not the nominal 288/day; the repo is public so
  hosted minutes are free; the twitterapi.io polling budget is per-item
  (config/press_sources.yml actions_wire) and re-derived per run, so run count
  does not multiply it. Cancelling a working feed to save zero dollars while the
  Chairman's X gate (t_fd170576, blocked) is the actual blocker inverts the
  dependency: the workflow is upstream of the gate, not downstream. The
  cancellation mechanism is the workflow's own timeout-minutes: 10 on the wire
  job, which is fixable in-place and reversible. The lane being dark to X is a
  documented structural gap (spool split-brain items-host.jsonl gitignored vs
  publisher folding git-tracked items.jsonl; systemd daemon never armed), not a
  reason to stop the poll — the poll-and-commit path is the half that now works.
alternatives:
  - option: "Disable the workflow (gh api PUT /actions/workflows/323156104/disable) until X gate t_fd170576 opens."
    why_not: "Stale premise: the lane books items as of runs #1231/#1232; disabling would starve the future open gate of spool; savings are nil (public repo, free hosted minutes, per-item API budget)."
  - option: "Keep running unchanged."
    why_not: "18/20 runs still die at the self-imposed 10-minute timeout before the publisher dispatch step; each such run books nothing — the poll half works, the dispatch half rarely fires."
  - option: "Raise the timeout and additionally arm the VPS systemd daemon to fill the host spool."
    why_not: "Arming the daemon is live-infrastructure change beyond this disposition's scope; the Actions-native path already books items without it. Revisit after the X gate opens."
evidence:
  - "Workflow identity live-read: id 323156104, path .github/workflows/marketing-press-wire.yml, state=active, total 1232 runs since 2026-07-29 (gh api repos/mastermindx-market-intelligence/macro/actions/workflows/323156104)."
  - "Run history 2026-11-08: last 20 = 18 cancelled / 2 success / 0 failure; #1231 2026-11-08T19:54:48Z success, #1232 2026-11-08T23:24:47Z success; cancellations spaced 3.5-7h (observed ~12 runs/day vs nominal 288/day cron)."
  - "Cancellation mechanism from job/step data (run #1230, id 42495192988): wire job timeout-minutes:10; steps 1-4 success, step 5 'run the press wire' cancelled at 10m02s, step 7 'dispatch the publisher' skipped."
  - "Booking + dispatch proof: run #1232 booked item ob-2026-11-08-bd4069e9e3 and dispatched marketing-publish.yml run 42535138274 (conclusion success; delivery-readback job skipped)."
  - "Header (origin master) documents the dark lane: 'The press wire has never once reached X ... Two independent reasons the lane is dark' (spool split-brain; daemon never armed)."
  - "X delivery unproven on the dispatched publish: all accounts last_x_visible=unknown; flagship accepted_unconfirmed 661; kelly channel disconnected; delivery-readback skipped."
  - "X gate card: kanban t_fd170576 'X posting gate — endpoint permission + entitlement + spend + credential custody (P0 / §12.5)' status=blocked (sqlite read of /Users/chriswong/.hermes/kanban.db, 2026-11-08)."
  - "Decision authority: Meta-CEO lane ruling 2026-11-08 recorded in kanban task t_cab13e33 body; mastermind-ceo lane owns the disable-or-fix call. Full evidence sweep preserved at .hermes/kanban/workspaces/t_cab13e33/evidence.md."
affects:
  - .github/workflows/marketing-press-wire.yml
  - .github/workflows/marketing-publish.yml
  - data/marketing/outbox/
  - data/marketing/press_wire/
confidence: high
reversibility: easy
decided_by: mastermind-ceo-disposition-20261108
decided_at: 2026-11-08
