---
workstream: "WS:CUSTOMER-DATA-BACKUP"
session: claude/ssd-customer-data-recovery-drill-a74367
model: claude-opus-5
ended_because: complete
mission: >
  Close GATE-1 with a real scratch restore: authoritative vendor backup/PITR facts,
  a real encrypted backup, a real scratch-Supabase restore, measured RTO/RPO,
  integrity verification, scratch destruction, durable receipt.
state_before: >
  PR #5733 merged 2026-08-15. Runbook and WS both recorded the two account-access
  facts as OPERATOR-BLOCKED. Linear MAS-33 Todo/unstarted. Assumed a real backup
  existed and only the drill was missing.
changed:
  - path: docs/RESTORE_RUNBOOK.md
    what: Vendor backup/PITR section filled from the Management API; scratch restore receipt filled with measured times; GATE-1 status flipped to CLOSED; stale RPO row corrected; the 36-night silent failure recorded.
  - path: agentos/workstreams/WS-CUSTOMER-DATA-BACKUP.md
    what: status blocked -> done; W1/W2 done with evidence; new W3 (alerting) and W4 (plan/auth.users); new landmines (key custody, pooler session mode, schema drift); do_not_redo extended.
  - path: scripts/backup_user_tables.py
    what: D1 fix — gate1_scratch_supabase now keys off the destination being a real Supabase project, not the transport.
  - path: tests/test_backup_user_tables.py
    what: Regression test for D1 across all four environment/dest combinations.
  - path: agentos/discoveries/DSC-AN-ARMED-BACKUP-TIMER-IS-NOT-A-BACKUP.md
    what: New discovery.
verified:
  - claim: The nightly backup had never succeeded; 36 nights of exit 2
    command: "ssh root@146.190.142.17 'systemctl show macro-user-backup.service -p Result -p ExecMainStatus; journalctl -u macro-user-backup.service'"
    result: "Result=exit-code, ExecMainStatus=2; every run 'BACKUP_ENCRYPTION_KEY is required'; units mtime 2026-08-15 12:49:49 UTC; /etc/macro-user-backup.env absent"
  - claim: R2 held zero backup artifacts
    command: "list_objects_v2 Bucket=mastermindx Prefix=private/user-table-backups/"
    result: "0 objects; control listing on the same credential returned 40+ prefixes and thousands of objects"
  - claim: Vendor layer has no recovery point
    command: "GET /v1/projects/fsldfzlxyavsuwqbceod/database/backups; GET /v1/organizations/ebhlfpiwuasxgkqcwsam"
    result: "pitr_enabled false, backups [], plan free"
  - claim: Real restore into a real scratch Supabase project succeeded
    command: "python -m scripts.backup_user_tables restore --backup-id user-tables-20260920T112413Z --dest-db-url \"$SCRATCH_DB_URL\" --i-am-restoring-into-scratch"
    result: "integrity pass, 9/9 tables, RTO 4s, RPO 288s, rc=0"
  - claim: Restored content is byte-identical to production, not merely equal in count
    command: "md5(string_agg(row::text order by row::text)) per table, production vs scratch"
    result: "identical on all 7 non-empty tables"
  - claim: Production was never written to
    command: "row counts re-queried in fsldfzlxyavsuwqbceod after the drill; pg_stat_user_tables in scratch"
    result: "production unchanged; no table outside the 9-table allowlist received inserts"
  - claim: Scratch destroyed
    command: "DELETE /v1/projects/hdxmdoodczwrvpobbbqp; GET /v1/projects"
    result: "HTTP 200; absent from list; direct GET 404 'Resource has been removed'"
unresolved:
  - "W3: no alerting on backup failure. 36 silent nights is the root defect."
  - "W4: plan free => no vendor backup, no PITR, no auth.users recovery path. Chairman decision."
  - "D5: production chart_layouts has team_id + visibility that no tracked migration creates."
do_not_redo:
  - "Do not re-run the drill to re-prove GATE-1. Receipt is in the runbook and MAS-33."
  - "Do not re-derive vendor plan/PITR by hand; the exact API calls are recorded."
  - "Do not restore via transaction-mode pooling (6543); session_replication_role will not hold."
danger_areas:
  - "BACKUP_ENCRYPTION_KEY exists only at /etc/macro-user-backup.env on the VPS (fingerprint 3fef2e6d82531251). Not yet confirmed in the operator password manager. If that box is lost before it is, every R2 copy is unrecoverable."
  - "The dump is the full customer table via the service-role key; it bypasses RLS."
prs: [5733]
decisions:
  - DEC:BACKUP-DUAL-SOURCE
discoveries:
  - DSC:SYSTEMD-ONESHOTS-USE-TIMEOUTSTARTSEC
  - DSC:AN-ARMED-BACKUP-TIMER-IS-NOT-A-BACKUP
---

## For the next session

GATE-1 is closed and the drill does not need repeating. What is still open is the
half that the drill exposed rather than solved:

1. **Alerting (W3).** The dump failed closed for 36 consecutive nights and nothing
   noticed. The unit is `Type=oneshot` with no `OnFailure=`. Until a failed night is
   loud, the same hole reopens the moment the key rotates or the env file is lost.
2. **The plan (W4).** On `free` there is no vendor backup and no PITR. `auth.users`
   is not in the dump and nothing sits behind it, so a full-project loss still cannot
   be recovered into a working product — the rows would come back, the logins would not.

The key custody item under `danger_areas` is the most urgent single line in this file.
