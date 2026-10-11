---
key: M2-RUNNER-LISTENER-SELF-CANCELS-ITS-JOB-AFTER-TEN-BROKER-POLL-FAILURES
claim: >
  A self-hosted GitHub Actions listener (runner 2.337.0 on the M2 Studio: mac-builder-4
  `~/actions-runner`, mac-builder-5 `~/actions-runner-2`, mac-builder-3 `~/actions-runner-3`,
  mac-builder-light `~/actions-runner-4`) cancels its OWN in-flight job when its broker
  long-poll fails ten consecutive times: every `GET broker.actions.githubusercontent.com/
  message?…&status=Busy` ends client-side with `The HTTP request timed out after 00:01:40`,
  roughly every sixth timeout logs `BrokerMessageListener] Retriable exception` plus a
  30-60 s sleep, and on the tenth retriable exception (~95 min after the listener started,
  deterministic per file: 63 timeouts / 10 catch / 9 sleeps / 1 shutdown) it logs
  `JobDispatcher] Shutting down JobDispatcher … cancel any running job`, the worker
  SIGINTs then SIGTERMs the running step, the job reports `completed with result:
  Canceled` with the sole annotation `The operation was canceled.`, the listener deletes
  its session and exits, and launchd (`actions.runner.*.plist` -> `runsvc.sh`) restarts it
  ~5 s later. Short requests from the same host keep succeeding throughout (91 `renewjob`
  POSTs per listener lifetime), so every liveness instrument reads green: the runner stays
  `online`, the org audit log holds no `workflows.cancel_workflow_run`, githubstatus shows
  no incident, no `timeout-minutes` fired, and the estate's
  `com.mastermind.runner-connectivity-watchdog` (which only kickstarts an idle listener
  GitHub reports OFFLINE) logged HEALTHY every 2 min through the whole outage. Since
  2026-10-09 21:47:04Z every poll on this host times out (an earlier episode ran 09-29 ->
  10-01; the 10-01 15:54Z listener lived 8 days with 67 timeouts total), so every job
  longer than one listener lifetime is cut: daily.yml collect / collect_tail / engine on
  10-10 (run 38014851530) and 10-11 (run 38100953149), and a closingbell job 10-10
  01:34Z. A second, independent blocker rejects even a completed scan: the commit-tail
  push dies on GH001 (`data/qledger/claims.jsonl` 122.92 MB in the scan tree, 104,521,374 B
  on main; Sol's #8042 / #8756).
falsifier: >
  For a job GitHub shows as `cancelled` on an M2 runner, read the listener log that was
  live at the cut: `grep -nE 'Shutting down JobDispatcher|completed with result' ~/actions-runner-2/_diag/Runner_20261011-031347-utc.log`
  (collect_tail 114376719298: shutdown 04:49:20Z, cut 04:49:27Z, `Job collect_tail
  completed with result: Canceled` 04:50:07Z). A cut with NO `Shutting down JobDispatcher`
  line within ~60 s before it in the live listener file, or an org audit-log row
  `workflows.cancel_workflow_run` for that run id (`gh api
  "orgs/mastermindx-market-intelligence/audit-log?phrase=action:workflows.cancel_workflow_run&per_page=20"`),
  disproves the mechanism for that job; a listener file with 10 `Retriable exception`
  lines and no shutdown disproves the ten-failure fuse; a day with zero
  `Runner_<date>-*-utc.log` restarts while jobs still get cut disproves the restart
  signature. Read-only: never restart a listener or dispatch/cancel daily.yml to test it.
so_what: >
  A `cancelled` nightly whose only annotation is `The operation was canceled.` with no
  audit-log cancel, no timeout-minutes and the runner still `online` is this mechanism
  until the listener log says otherwise — diagnose from `~/actions-runner*/_diag/`
  (listener start banner = a restart; count `Retriable exception` per file), not from the
  workflow, the job caps, the watchdog log or the API. Nothing in daily.yml can prevent a
  runner-side cancel: the levers are the host path to the broker (VPN / filter network
  extensions, NAT idle-drop; packet-capture one `/message` poll), the runner service env
  (`GITHUB_ACTIONS_RUNNER_HTTP_TIMEOUT` / `_HTTP_RETRY` in Runner.Sdk.dll 2.337.0 — a
  stop-gap that lengthens the fuse), and a watchdog that counts `Shutting down
  JobDispatcher` while a Worker is live — all operator acts on runner-host services, never
  a seat's. Any proof that waits on "the next nightly" (W2C owner replay, manifest
  republish, data-health, Prophet freshness) is gated on BOTH this and the GH001 push
  rejection; a seat records the gate and the evidence once (#8748 comment 6114287529) and
  does not re-investigate or re-dispatch.
kind: landmine
verified_at: 2026-10-11
verified_by: >
  Read-only reads on the M2 Studio 2026-10-11 ~21:0x-21:5xZ: `~/actions-runner-2/_diag/
  Runner_20261011-031347-utc.log` (04:49:10Z renewjob back-off, 04:49:20Z Catch
  exception -> Shutting down JobDispatcher, 04:50:07Z `Job collect_tail completed with
  result: Canceled`, `Deleting Runner Session`), `Worker_20261011-031429-utc.log`
  (04:49:20Z Cancellation/Shutdown message received -> SIGINT 18518 -> 04:49:27Z SIGTERM),
  `~/actions-runner-4/_diag/Runner_20261011-002317-utc.log` (03:12:36Z shutdown -> 03:14:26Z
  `Job collect … Canceled`) and `Runner_20261011-031432-utc.log` (04:58:46Z shutdown ->
  05:19:56Z `Job engine … Canceled`); 10-10 falsifier pass on runner-2 (03:27:46Z /
  05:07:08Z) and runner-4 (01:33:42Z closingbell, 05:15:16Z engine); per-day restart
  census of `Runner_*-utc.log` 09-28 -> 10-11; `gh api actions/runs/38100953149/jobs`
  and `…/38014851530/jobs` (startedAt / completedAt / runner_name); org audit-log query
  (no cancel rows); githubstatus incidents.json (no 10-09 -> 10-11 Actions incident);
  collect_tail job log 04:49:53Z GH001 line. Posted as #8748 issuecomment-6114287529.
scope: [macro, ".github/workflows/daily.yml", ".github/workflows/closing-bell.yml", "runner-host:m2studio ~/actions-runner*/_diag/**", "scripts/prophet_rescue.py"]
confidence: verified
---

Observed by seat fd47d431 (Market-Intelligence Institutional Buildout) as the critical-path
gate on its 10-12 post-nightly proofs; the nightly, the runner hosts and the GH001 lane
(#8042 / #8756) all belong to other owners. The signature is cheap to check and the
instruments that normally answer "why did it die" are all silent here — which is the finding.
