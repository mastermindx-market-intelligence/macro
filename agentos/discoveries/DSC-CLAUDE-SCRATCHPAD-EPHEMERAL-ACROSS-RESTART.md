---
key: CLAUDE-SCRATCHPAD-EPHEMERAL-ACROSS-RESTART
claim: >
  The Claude Code session scratchpad under /private/tmp/claude-501/<session>/scratchpad is wiped
  when the desktop app restarts, together with every background agent, Monitor and controller
  process of that session; remote fabric lanes launched under nohup on the lane hosts keep
  running and their RESULT.md, stdout and rc files persist on the host and in the kit's
  ext/state/remote_sub and ext/lanes directories.
falsifier: >
  After a Claude desktop restart run `ls /private/tmp/claude-501/<session>/scratchpad` and find
  the previous contents intact, or run `ssh mmx-ubuntu0 'cat ~/lanes/ext/lanes_<run-id>.rc'` for a
  lane launched before the restart and find no rc file written after it; either disproves the
  respective half of the claim.
so_what: >
  Treat the scratchpad as a working cache: mirror packets, results and launch scripts to a
  persistent directory (this programme used the meta-ceo-b handoff kit (handoff_kits/meta-ceo-b-2026-09-08) ext/ce-scratch-1013/) after every change,
  and recover lane outcomes from the host files, not from local controller output. Re-arm
  Monitors and re-spawn orchestrators from the persisted progress files after a restart.
confidence: verified
kind: landmine
verified_at: 2026-10-13
verified_by: >
  Session 6dfa7fe4 restart on 2026-10-13: scratchpad empty afterwards; wave-4 lanes
  ce-bench-1013b, ce-paint2d-1013, ce-model2d-1013, ce-lwcprim2-1013, ce-mig-rev-1013 found
  complete on their hosts (~/lanes/wt/<run-id>/RESULT.md, ~/lanes/ext/lanes_<id>.rc) and
  harvested from there; memory note chart-engine-fanout-2026-10-12.md § "Scratchpad is
  ephemeral".
scope:
  - fabric
  - orchestration
---

Recovery recipe used: rebuild packets from the transcript, harvest `RESULT.md` per lane host,
re-run the controller only for lanes whose `.rc` file was absent.
