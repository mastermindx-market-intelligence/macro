---
key: LANE-RECONCILIATION-HOLD-CLOSES-HOST
claim: >
  A fabric lane that dies with rc=76 REMOTE_CLEANUP_UNPROVEN leaves a
  mastermind.local_lane_reconciliation_hold.v1 marker under ~/lanes/ext/active/ on that host,
  and while the marker exists every new lane on the host is refused at admission with
  reasons ["reconciliation_hold_present"], regardless of load, temperature or pool.
falsifier: >
  ssh mmx-ubuntu3 'ls ~/lanes/ext/active/' shows the ce-decor-1012d marker; then
  `pool remote ubuntu3 glm <any packet> '~' glm-5.3 --run-id <fresh-id>` from
  handoff_kits/meta-ceo-b-2026-09-08/ext returns rc=75 and
  ext/lanes/<fresh-id>.remote.stdout carries reasons ["reconciliation_hold_present"].
  The claim is disproved if a lane is admitted on the host while the marker exists, or if
  lane_runtime.py exposes a general release path that is not keyed to one incident.
so_what: >
  After any rc=76 death, treat that host as closed to the whole fleet: relaunch the package
  on another host with a NEW run-id suffix, record the dead lane with
  `pool ledger outcome <id> --accepted-by none --retries 1`, and report the marker to the
  fabric owner. Never hand-delete the marker and never admin-bypass admission; the only
  reconcile code (lane_runtime.reconcile_preexec_hold, native_preexec_reconcile.py) is
  hard-wired to one earlier ubuntu2 incident.
kind: runtime
verified_at: 2026-10-12
verified_by: >
  handoff_kits/meta-ceo-b-2026-09-08/ext/lanes/ce-m01-1012b.remote.stdout (refusal payload,
  05:2xZ 2026-10-12) and ext/lane_runtime.py evaluate_admission / hold_for_reconciliation /
  reconcile_preexec_hold; marker written 2026-10-12T05:06:23Z after lane ce-decor-1012d
  (pid 961806) was killed on ubuntu3 while other sessions pushed load1 to 17-24.
scope:
  - macro
  - handoff_kits/meta-ceo-b-2026-09-08/ext/lane_runtime.py
  - WS:NATIVE-CHART-ENGINE
confidence: verified
---

The hold is a real control, not a bug to route around: it exists because the dead lane's
cleanup could not be proven and a second lane on the same host could inherit its effects.
What is missing is an operator-facing reconcile command; until one exists, a single rc=76
death removes a whole host from the fleet.
