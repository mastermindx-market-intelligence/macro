---
key: IW2-CONSISTENT-BACKUP-SNAPSHOT
question: How can IW2 acquire a restorable cross-table snapshot without breaking the existing nightly backup or historical archives?
answer: >
  Extend the existing backup script/store with an explicit thirteen-table v2
  SQL snapshot mode. Read all rows and counts in one SELECT; restore in one
  transaction with exact row-multiset comparison. Keep the default nine-table
  REST timer and v1 archive reader compatible. Authorized Management API
  responses may enter via private stdin; credentials stay in their existing
  stores and actual transport identity remains an independent acceptance fact.
rationale: >
  The installed script and twenty current manifests cover nine tables, excluding
  investigations, investigation_revisions, investigation_mutation_receipts and
  chart_layout_revisions. Independent REST reads cannot establish one consistent
  snapshot across those linked records. The installed timer has no direct DB URL.
  An explicit snapshot path enables the migration prerequisite without copying
  a Management token onto the backup host or silently changing scheduled coverage.
alternatives:
  - option: Replace the global allowlist with thirteen names
    why_not: Breaks old archive restores and still gives no cross-table snapshot in REST mode.
  - option: New backup script, timer or storage prefix
    why_not: Duplicates existing custody and recovery lifecycle without solving consistency.
  - option: Install a new production RPC or copy a Management credential to the timer
    why_not: Adds a schema or credential effect that the read-only snapshot does not need.
evidence:
  - "Terminal PR 804 comment 6078460402 joins installed script identity and returns the backup repair to IW2."
  - "Macro PR 7532 original head 21d35c48; exact-head Fabric compatibility return iw2-backup7532-compat-20261009 accepted for its bounded analysis."
  - "python3 -m pytest tests/test_backup_user_tables.py tests/test_backup_iw2_snapshot.py -q --override-ini addopts='' => 43 passed including local PostgreSQL atomic failure, precise numeric roundtrip, typed IW2 references and source timezone."
affects: [WS:CUSTOMER-DATA-BACKUP, WS:DEEPVUE-INTELLIGENCE-WORKSPACE]
confidence: high
reversibility: easy
decided_by: 01a104c8-6e11-7e52-93c1-6b8dbc45bb9c
decided_at: 2026-10-09
---

The source tests are synthetic. No production snapshot, scratch Supabase restore,
nightly IW2 RPO, 0030 permission, or G0-G9 acceptance is implied. The historical
September nine-table drill remains scoped. DEC:BACKUP-DUAL-SOURCE still governs
the default timer; this decision adds an explicit consistent-capture path.
