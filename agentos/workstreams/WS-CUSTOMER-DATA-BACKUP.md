---
key: CUSTOMER-DATA-BACKUP
title: Customer-data backup and restore (MMX-001 / GATE-1)
objective: >
  A nightly encrypted dump of the nine customer/billing tables reaches private R2
  with ≥30-day retention, a restore runbook names exact commands, and one restore
  into a scratch non-production Supabase project has been performed with measured
  RTO/RPO. Done only when that scratch receipt exists — a written procedure alone
  does not close GATE-1.
status: active
program: shared-auth-entitlements
repos: [macro]
owner: ops
class: build
blast_radius: irreversible
ambiguity: specified
owns_paths:
  - scripts/backup_user_tables.py
  - app/deploy/macro-user-backup.service
  - app/deploy/macro-user-backup.timer
  - docs/RESTORE_RUNBOOK.md
blocked_by: []
waves:
  - id: W1
    title: Repo-side dump job, systemd timer, runbook, fail-closed tests
    status: done
    pr: 5733
  - id: W2
    title: Scratch-Supabase restore drill + vendor PITR fact
    status: done
    depends_on: [W1]
    evidence: >
      2026-09-20. Vendor facts read from the Supabase Management API (plan free,
      pitr_enabled false, backups []). Backup user-tables-20260920T112413Z restored into
      scratch project mmx-restore-scratch-20260920 (ref hdxmdoodczwrvpobbbqp): integrity
      pass, 9/9 tables, RTO 4s, RPO 288s. Independently verified by re-querying scratch
      and by content-level md5 equality against production on all 7 non-empty tables.
      Production unchanged. Scratch destroyed, GET -> 404. Linear MAS-33.
  - id: W3
    title: Backup-failure alerting (the 36 silent nights)
    status: todo
    depends_on: [W2]
    note: >
      The dump failed closed every night from 2026-08-15 to 2026-09-20 and nothing
      alerted. Needs OnFailure= on the unit or an R2 freshness check. This is the
      defect that made GATE-1 a fiction, not the missing drill.
  - id: W4
    title: Vendor-side recovery point (plan) + auth.users recovery path
    status: todo
    note: >
      On plan free there is no vendor backup and no PITR, so auth.users has no
      recovery path at all - it is not in the dump and nothing sits behind it.
      Requires a plan decision (Pro) - Chairman call, not a worker call.
  - id: W5
    title: Consistent IW2 snapshot and independently verified restore
    status: in_progress
    pr: 7532
    depends_on: [W2]
    note: >
      Root 01a104c8-6e11-7e52-93c1-6b8dbc45bb9c owns the existing carrier's
      integration. The installed nine-table REST timer cannot cover IW2's four
      tables. Explicit thirteen-table SQL snapshot and backward-compatible restore
      source is being qualified. Production capture, approved scratch restore,
      exact-reference readback and ongoing IW2 coverage remain unverified.
decisions:
  - DEC:IW2-CONSISTENT-BACKUP-SNAPSHOT
  - DEC:BACKUP-DUAL-SOURCE
discoveries:
  - DSC:SYSTEMD-ONESHOTS-USE-TIMEOUTSTARTSEC
  - DSC:AN-ARMED-BACKUP-TIMER-IS-NOT-A-BACKUP
landmines:
  - "NEVER restore into production project fsldfzlxyavsuwqbceod. The script refuses that ref; do not add an override."
  - "auth.users is not in the dump. A scratch project needs matching users or session_replication_role=replica."
  - "Losing BACKUP_ENCRYPTION_KEY loses the R2 copies. The live key was generated 2026-09-20 and lives ONLY at /etc/macro-user-backup.env (0600) on the API VPS; sha256 fingerprint 3fef2e6d82531251. It must be in the operator password manager."
  - "Use the Supabase pooler in SESSION mode (port 5432) for restore. Transaction mode (6543) can route each statement to a different connection, so SET session_replication_role = replica will not hold across the INSERT and the auth.users FKs will fire."
  - "The September chart_layouts drift attribution is historical and not current proof; Terminal migration 0022 now owns team_id/visibility. Match actual source/target catalog identity for each restore."
do_not_redo:
  - "Do not invent a second backup script or a parallel timer. Extend scripts/backup_user_tables.py and macro-user-backup.*."
  - "Do not claim GATE-1 closed from the in-process fixture drill. That receipt is environment=in-process-fixture."
  - "Do not re-run the scratch restore drill to 're-prove' GATE-1. It was performed and verified on 2026-09-20; the receipt is in docs/RESTORE_RUNBOOK.md and Linear MAS-33. Re-run only if the backup format, the table allowlist, or the restore path changes."
  - "Do not re-derive the vendor plan/PITR facts by hand. They are recorded in the runbook with the exact Management API calls that produced them."
artifacts:
  - scripts/backup_user_tables.py
  - app/deploy/macro-user-backup.service
  - app/deploy/macro-user-backup.timer
  - docs/RESTORE_RUNBOOK.md
  - tests/test_backup_user_tables.py
next_action: >
  Review and qualify the existing PR 7532 snapshot extension, then complete a
  source-bound encrypted production capture and approved scratch restore with
  independent IW2 reference readback before the held 0030 migration action.
  Historical W2 remains accepted only for nine tables. W3 alerting and W4
  vendor/auth recovery remain separate; no plan purchase is authorized here.

---

## Scope

WS-1 of `research/MASTERMIND_RED_TEAM_REMEDIATION_PLAN.md`. Isolated from other
Wave-1 lanes. No auth/billing/Prophet/Radar redesign. No production deploy.
