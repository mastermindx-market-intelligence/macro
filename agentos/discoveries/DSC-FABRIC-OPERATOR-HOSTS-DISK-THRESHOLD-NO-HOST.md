---
key: FABRIC-OPERATOR-HOSTS-DISK-THRESHOLD-NO-HOST
claim: >
  Fabric auto-placement (`pool remote auto`) refuses operator-tier lanes (cursor, grok, glm) with
  NO_HOST when every operator-eligible Ubuntu host is below the placement free-disk threshold
  (observed on 2026-10-13: ubuntu0 282.5 GiB < 300 GiB), while an explicit host argument
  (`pool remote ubuntu0 …`) bypasses the auto-placement disk gate and still runs the
  ECONOMIC_POLICY and LEASE gates; executor-tier pools (bailian, minimax) auto-place onto the
  Mac hosts (mb, minis) which have no such refusal.
falsifier: >
  Run `python3 ext/host_pick.py --mode grok --explain` from the meta-ceo-b kit while every operator
  host reports free disk below the threshold in ext/hosts.json and get a host instead of NO_HOST, or
  run `pool remote ubuntu0 grok <packet> <cwd> grok-4.6 --dry-run` on such a host and be refused for
  disk alone. Either disproves the claim.
so_what: >
  When auto placement answers NO_HOST for an operator lane, place it explicitly on the host with
  the most free disk instead of re-planning the work onto the seat or onto a lower tier; record
  the explicit placement in the orchestrator's progress file so the ledger outcome names the
  real host. Reclaim lane clones under ~/lanes/wt on the Ubuntu hosts before a large fan-out.
confidence: verified
kind: runtime
verified_at: 2026-10-13
verified_by: >
  OPUS-P1 progress 04:55Z ("auto placement NO_HOST on disk thresholds", explicit host=ubuntu0
  launch succeeded, ECONOMIC_POLICY allowed, LEASE_OK); OPUS-MIG advisory 04:56Z listing
  ubuntu0 disk 282.5<300 for cursor/grok; controller logs
  the meta-ceo-b handoff kit (handoff_kits/meta-ceo-b-2026-09-08) ext/state/remote_sub/ce-integrate3b-1013.log and ce-kinetic-1013.log.
scope:
  - fabric
  - orchestration
---

Caveat: the executor tier auto-placed onto `mb` for ce-mig-fix-1013 the same day, so the
threshold is specific to the operator-eligible Ubuntu pool, not a fleet-wide brake.
