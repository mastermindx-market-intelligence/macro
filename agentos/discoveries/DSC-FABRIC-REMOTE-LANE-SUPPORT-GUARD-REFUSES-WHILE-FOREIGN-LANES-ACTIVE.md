---
key: FABRIC-REMOTE-LANE-SUPPORT-GUARD-REFUSES-WHILE-FOREIGN-LANES-ACTIVE
claim: >
  `pool remote <mb|m1> ...` refuses admission with rc=75 and the log line
  `SUPPORT_STALE_ACTIVE_REFUSED active=N` whenever the remote executor-surface support manifest
  (`remote_sub.sh`: SUPPORT_FILES + `../orch/fabric/pools.yaml` sha256, default `--max-age 600`)
  is older than the max age AND any lane marker exists under `~/lanes/ext/active/` on that host —
  including markers owned by OTHER orchestrators. The refusal is independent of the free-slot
  count: a host with 1 of 2 slots free still refuses. Retrying on a timer never clears it while
  foreign lanes stay active, because the guard refreshes support only when the host is idle.
falsifier: >
  With `ssh <host> 'ls ~/lanes/ext/active'` showing at least one foreign marker, run
  `POOL_ORCHESTRATOR_ID=<id> pool remote <host> minimax <brief> /Users/chriswong/lanes/wt/<wt>
  --out /tmp/lane.out` and observe `LEASE_OK` followed by `LAUNCH` (rc != 75) without
  `SUPPORT_STALE_ACTIVE_REFUSED` in the log; or observe the refusal disappearing after only a
  timed retry with the same foreign markers still present. Either falsifies the claim.
so_what: >
  Read rc=75 with this line as a capacity-owner reconciliation condition, not a transient slot
  wait: stop timed retries (Sol ruled NO_DELTA_LOOP on Mastermind #959, comment 5814585111),
  never touch or clear foreign markers or shared support yourself, and either route the bounded
  delta to the incumbent custodian (permitted for a small repair on the same branch) or wait for
  the pool/support owner to refresh. Do not raise `--max-age` or pass `--refresh` on a host that
  has active foreign lanes — that overwrites support other orchestrators are running on.
kind: landmine
verified_at: 2026-09-24
verified_by: >
  Fable delivery principal, 2026-09-24 12:46Z-13:07Z, IAC-1 round 4D placement for Mastermind
  PR #959: four attempts (m1 12:46, m1 12:47, mb 13:07, m1 13:07) each logged `LEASE_OK
  SUPPORT_STALE_ACTIVE_REFUSED SCP_FAILED rc=75`; `ssh <host> 'ls ~/lanes/ext/active'` showed
  foreign markers (mb: b_f11_10a, mo_a3_mor2b_a2_producer; m1: 6872 mo_a3_f04_x1_review, 7903
  fin_d1b_mockup) with one slot free on m1; the remote worktree stayed clean at 101def5 and no
  worker started. The delta was then implemented by the custodial principal directly
  (Mastermind #959 head d82a2e70).
scope:
  - Mastermind
  - agent-fabric-end-to-end-fable-integration-20260913-sol-001
  - ~/lanes/ext (mb, m1 remote construction lanes)
confidence: verified
---

# The remote lane support guard refuses every launch while foreign lanes are active

`SUPPORT_STALE_ACTIVE_REFUSED` is a support-owner reconciliation condition, not a slot wait:
timed retries cannot clear it and refreshing support under foreign lanes is not yours to do.
