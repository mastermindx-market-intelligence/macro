---
key: AN-ARMED-BACKUP-TIMER-IS-NOT-A-BACKUP
claim: >
  A systemd backup timer that is `enabled` and `active`, with a healthy `NEXT`
  elapse in `list-timers`, proves only that the SCHEDULER works — it says nothing
  about whether a backup exists. Macro's `macro-user-backup.timer` self-armed on
  2026-08-15 12:49:49 UTC via `update.sh` and reported enabled/active for 36
  consecutive nights while `macro-user-backup.service` exited 2 every single run
  (`backup_user_tables: BACKUP_ENCRYPTION_KEY is required`) because the operator
  env file `/etc/macro-user-backup.env` was never created. R2
  `private/user-table-backups/` held 0 objects the whole time. The fail-closed
  design worked exactly as intended and was completely invisible: the unit is
  `Type=oneshot` with no `OnFailure=`, so a failed run leaves the timer healthy and
  emits nothing anyone reads. Compounding it, the vendor layer was also empty —
  Supabase org on plan `free`, `pitr_enabled: false`, `backups: []` — so 483 live
  customer/billing rows had zero recovery coverage on BOTH layers and the effective
  RPO was unbounded while the runbook declared 24 h.
falsifier: >
  Any of: a successful object appearing under `private/user-table-backups/` during
  2026-08-15..2026-09-20; `systemctl show macro-user-backup.service -p Result`
  returning `success` before 2026-09-20T11:24Z; a `BACKUP_R2_*` override pointing
  the job at a different bucket that did hold artifacts. All three were checked and
  none held — the R2 credential was control-tested (it lists 40+ prefixes and
  thousands of objects in the same bucket), and no `BACKUP_R2_*` is defined on the
  VPS or in either repo.
so_what: >
  Never accept timer state, unit state, or "the job is deployed" as evidence that a
  backup exists. The only evidence is an ARTIFACT: list the destination prefix and
  check the newest object's age, or decrypt-and-verify a specific backup id. Assert
  freshness at the destination, not liveness at the scheduler. Every fail-closed job
  whose failure is invisible needs `OnFailure=` or an external freshness check, or it
  is indistinguishable from a job that never ran — and the more correct its
  fail-closed behaviour, the quieter the hole it leaves. Check the vendor layer
  separately and with authority (`GET /v1/projects/{ref}/database/backups`), because
  a plan downgrade silently removes the safety net people assume is underneath.
