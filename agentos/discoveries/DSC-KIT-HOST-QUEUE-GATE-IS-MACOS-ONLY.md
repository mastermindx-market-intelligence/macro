---
key: KIT-HOST-QUEUE-GATE-IS-MACOS-ONLY
claim: >
  The B-kit lane queue daemon (handoff kit meta-ceo-b-2026-09-08, ext/host_queue.sh) never opens
  its gate on a Linux lane host because gate_open() reads load with `sysctl -n vm.loadavg`, a
  macOS-only key, so every ubuntu1/ubuntu2 queue entry sits in GATE_WAIT forever.
falsifier: >
  On ubuntu1 run `sysctl -n vm.loadavg` (expect an error, not three numbers) and watch
  host_queue_ubuntu1.log for a GATE_OPEN line after a queued lane; a gate that opens disproves
  this.
so_what: >
  Launch Linux lanes directly — `LANE_ORCH_ID=<seat> bash remote_lane_v8.sh ubuntu1|ubuntu2
  <label>` as a background task whose exit is the watcher — instead of queuing them; a queued
  Linux lane is a lane that will never start. Fixing the daemon (read /proc/loadavg on Linux) is
  a kit change, not a session hack; never edit a running ext/*.sh in place.
kind: landmine
verified_at: 2026-10-06
verified_by: >
  host_queue_ubuntu1.log GATE_WAIT lines with load=? for the whole 2026-10-06 04:xxZ window;
  daemon pid 63740 identified with `ps -o command= -p` and stopped; SEAT_NOTE appended to the
  same log; direct remote_lane_v8.sh launches admitted on both hosts within the same minute.
scope:
  - handoff kit meta-ceo-b-2026-09-08 (ext/host_queue.sh, ext/remote_lane_v8.sh)
  - ubuntu1 / ubuntu2 lane hosts
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
confidence: verified
---

Observed while launching the 2026-10-06 wave-1 census lanes for Mastermind #1258: three queued
lanes sat idle for ~20 minutes with `load=?` in every GATE_WAIT line. The kit's macOS hosts
(m2studio, mini2) are unaffected.
