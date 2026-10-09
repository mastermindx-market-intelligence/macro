# Restore runbook — customer and billing tables (MMX-001 / GATE-1)

**NEVER restore into production.** The live Supabase project ref is
`fsldfzlxyavsuwqbceod`. `scripts/backup_user_tables.py restore` refuses any
destination that contains that ref, matches `SUPABASE_URL` /
`SUPABASE_DB_URL` / `DATABASE_URL`, or shares their host. There is no override
flag.

This document is the operator procedure. A written procedure is **not** GATE-1.
GATE-1 passes only when a restore has been performed into a scratch
non-production Supabase project and the receipt below is filled with measured
times. **That happened on 2026-09-20 — GATE-1 is CLOSED.** Both facts that
require account access are now recorded below from authoritative vendor state.
That historical result covers the original nine tables only. **IW2 recovery
acceptance remains OPEN** until a current thirteen-table snapshot is restored
and independently checked in an approved scratch destination.

---

## What is protected

Nightly job: `python -m scripts.backup_user_tables dump`

Tables (allowlist; the job will not dump anything else):

| Table | Why it is here |
|---|---|
| `profiles` | Account profile / identity row |
| `watchlists` | User list containers |
| `watchlist_symbols` | Tickers on those lists |
| `chart_layouts` | Saved chart state |
| `saved_scripts` | Saved editor scripts |
| `alerts` | User alerts |
| `favorites` | Favorites |
| `user_entitlements` | Who paid, which tier, Stripe customer id |
| `stripe_events` | Webhook idempotency ledger |

`auth.users` is owned by Supabase Auth (GoTrue) and is **not** in this dump. A
scratch project must already have matching users, or the SQL restore must run
with `session_replication_role = replica` (the `psql` path does). A full
identity recovery still needs the vendor backup / PITR for `auth`.

`app/deploy/live-rollback.sh` recovers published artifacts only. It never
touches Postgres.

### IW2 snapshots and historical archives

The default nightly command and its installed timer retain the original nine
tables. Its REST reads are separate requests, so this path does **not** claim
a consistent IW2 backup. The installed service currently has no direct database
URL. Do not silently change the timer, copy a Management token into it, create
another backup store, or represent the September nine-table drill as IW2 proof.

An explicit `--table-set iw2` adds `chart_layout_revisions`, `investigations`,
`investigation_revisions`, and `investigation_mutation_receipts`. All thirteen
tables and counts come from **one read-only SQL SELECT**, with its transaction
snapshot identifier and source timestamp. Separate per-table requests and
`--allow-missing` are refused for this set. Its archive schema is
`mmx.user_table_backup.v2`; old `v1` nine-table archives still verify and restore.
The reader binds archive members, table hashes/counts, schema, sidecar, and backup
identity instead of treating absent IW2 tables as empty historical coverage.

With an already-authorized source connection in its existing secret slot:

```bash
python -m scripts.backup_user_tables dump --table-set iw2 --mode pg_dump \
  --source-project-ref fsldfzlxyavsuwqbceod
```

This mode captures the canonical JSONL payload through one SQL statement. It
does not attach a separately timed `pg_dump.sql` sibling to an IW2 archive.

Where the established authorized transport is the Supabase Management API,
generate the same read-only query:

```bash
python -m scripts.backup_user_tables snapshot-query \
  --source-project-ref fsldfzlxyavsuwqbceod
```

Submit that exact SELECT with `read_only: true` through the existing authenticated
transport. Keep the response private and in memory; pipe it into the existing
backup host's stdin while that host loads its own existing encryption/R2 secret
slots. Do not log the response, persist plaintext customer rows, put credentials
in argv, or move the Management token or encryption key between hosts.

```bash
# stdin is the exact private response of the authorized read-only query
python -m scripts.backup_user_tables dump --table-set iw2 --mode snapshot \
  --source-project-ref fsldfzlxyavsuwqbceod
```

The importer checks source identity, snapshot metadata, exact table coverage,
row shapes and counts, and records the response/query hashes. These fields are
**not independent transport attestation**: the parent must retain the actual
authenticated endpoint/project/query identity and capture time. A fabricated
or fixture capsule cannot satisfy production acceptance. This manual capture
does not establish nightly IW2 coverage or a new 24-hour IW2 RPO.

IW2 restores require `--dest-db-url` into an approved non-production scratch
database. All inserts and exact JSON row-multiset comparisons execute in **one
transaction**; a constraint failure or content mismatch rolls it back. The
receipt distinguishes transactional/content verification from legacy REST
row-count verification. Schema must already match the captured production
schema, and source/target catalog evidence remains part of the drill. Do not
apply an unapplied migration merely to manufacture a scratch schema.

Before approving migration 0030, retain the immutable encrypted object and its
manifest/hash, verify it after download, restore into the approved scratch
destination, and independently read back all four IW2 tables and their exact
head/revision/receipt/retained-layout references. Historical external Thesis or
evidence references remain their owners' responsibility; `auth.users` is still
outside this backup. A local synthetic test or metadata-only R2 listing does
not close this gate. Preserve the original production migration hold.

---

## Declared RPO / RTO

| Metric | Declared target | Meaning |
|---|---|---|
| **RPO** | **24 hours** | Nightly dump at 05:17 UTC. Worst case after a successful dump: lose the day's writes. First successful dump: 2026-09-20T11:24:13Z — before that RPO was unbounded, and there is no Supabase-managed fallback behind it (plan `free`, PITR off, zero vendor backups — see § "Vendor backup / PITR"). |
| **RTO** | **30 minutes** | Time from "we have a backup id and a scratch project with schema applied" to "row counts match the manifest". Does not include creating a new Supabase project or re-pointing production DNS. |

These are targets, not measurements. Measured values live in the receipt
sections below.

---

## Status of GATE-1 facts that need account access

| Fact | Status |
|---|---|
| Supabase plan / PITR | **CONFIRMED 2026-09-20** — read from the Supabase Management API. See § "Vendor backup / PITR". |
| scratch-supabase restore | **PASS 2026-09-20** — real backup restored into `mmx-restore-scratch-20260920`, verified, scratch destroyed. See § "Scratch-Supabase restore receipt". |

### What this drill uncovered

The drill could not start as written, because **there was no backup to restore**.
`macro-user-backup.{service,timer}` self-armed on 2026-08-15 12:49:49 UTC and every
run since had failed `BACKUP_ENCRYPTION_KEY is required` → exit 2, because
`/etc/macro-user-backup.env` had never been created. R2
`private/user-table-backups/` held **0 objects**. 36 consecutive nights, zero
successes, and no alert. Combined with the vendor facts below, customer/billing
data had **zero recovery coverage on either layer** and the effective RPO was
unbounded, not the declared 24 h.

The key was generated on the VPS and installed at `/etc/macro-user-backup.env`
(0600, root:root) on 2026-09-20, the first real dump succeeded at 11:24:13Z, and
the restore drill ran against it. **The key must live in the operator password
manager — losing it makes every R2 copy unrecoverable.**

Still owed after this drill:

1. **Backup-failure alerting.** 36 silent nights is the real defect. `OnFailure=`
   on the unit, or a freshness check on the R2 prefix, so a fail-closed night is loud.
2. **The plan.** On `free` there is no vendor backup and no PITR, so `auth.users`
   has no recovery path at all — it is not in this dump and nothing sits behind it.
   Pro is the only fix for that half.

---

## Nightly dump (VPS)

Units: `app/deploy/macro-user-backup.service` + `.timer` (05:17 UTC,
`RuntimeMaxSec=900`, `TimeoutStartSec=900`). `update.sh` self-arms the timer
on the box where `macro-api.service` is enabled.

Create `/etc/macro-user-backup.env` (mode 0600, root-only):

```bash
umask 077
cat > /etc/macro-user-backup.env <<'EOF'
BACKUP_ENCRYPTION_KEY=<openssl-rand-hex-32>
SUPABASE_DB_URL=<postgres-connection-string-with-password>
# Optional dedicated R2 (otherwise the job uses R2_* from /etc/macro-api.env):
# BACKUP_R2_ENDPOINT=https://<accountid>.r2.cloudflarestorage.com
# BACKUP_R2_ACCESS_KEY_ID=...
# BACKUP_R2_SECRET_ACCESS_KEY=...
# BACKUP_R2_BUCKET=mastermindx
# BACKUP_R2_PREFIX=private/user-table-backups/
EOF
chmod 600 /etc/macro-user-backup.env
```

The encryption key must be at least 16 characters. Store a copy in the
operator password manager. Without it the ciphertext is unrecoverable.

Preferred dump path is the direct DB URL (`pg_dump` SQL sibling + `psql`
JSONL). If only `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` are set, the job
uses PostgREST. Either way the published object is an openssl
AES-256-CBC-PBKDF2 archive under `private/user-table-backups/`. That prefix
must not be mapped on the public R2 CDN.

Manual dump (same command the unit runs):

```bash
sudo systemctl start macro-user-backup.service
# or, from /opt/macro with the env files loaded:
set -a
source /etc/macro-api.env
source /etc/macro-user-backup.env
set +a
python -m scripts.backup_user_tables dump
```

List published backups:

```bash
python -m scripts.backup_user_tables list
```

Decrypt-and-hash check (does not write to any database):

```bash
python -m scripts.backup_user_tables verify --backup-id user-tables-YYYYMMDDTHHMMSSZ
```

Retention: the job deletes objects under the prefix older than 30 days. Do not
pass `--retention-days` below 30; the process exits 2. Also set an R2
lifecycle rule on `private/user-table-backups/` to 30 days as a second
enforcement.

---

## Restore into scratch

Preconditions: scratch project exists, schema applied, `BACKUP_ENCRYPTION_KEY`
matches the dump, and you can read the private R2 prefix (or you have a
`--local-dir` copy).

```bash
export BACKUP_ENCRYPTION_KEY='<same key used to dump>'
export SCRATCH_DB_URL='postgresql://postgres.<scratch-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres'
# If listing/fetching from R2, the host also needs BACKUP_R2_* or R2_*.
# If you copied the two objects off R2 first:
#   --local-dir /var/tmp/mmx-backups

python -m scripts.backup_user_tables restore \
  --backup-id user-tables-YYYYMMDDTHHMMSSZ \
  --dest-db-url "$SCRATCH_DB_URL" \
  --i-am-restoring-into-scratch \
  --write-receipt /tmp/mmx-restore-receipt.json
```

REST alternative when you have the scratch API URL + its service-role key
instead of a DB URL:

```bash
export SUPABASE_SCRATCH_SERVICE_ROLE_KEY='<scratch service role>'
python -m scripts.backup_user_tables restore \
  --backup-id user-tables-YYYYMMDDTHHMMSSZ \
  --dest-supabase-url "https://<scratch-ref>.supabase.co" \
  --i-am-restoring-into-scratch \
  --write-receipt /tmp/mmx-restore-receipt.json
```

The process prints a JSON receipt with `backup_id`, redacted dest, `started_at`,
`ended_at`, `rto_seconds`, `rpo_seconds`, and per-table
`expected` / `restored` / `ok`. `integrity` must be `pass`. If any table is
`ok: false`, the restore did not succeed.

Production URLs fail closed even with `--i-am-restoring-into-scratch`.

After a successful scratch restore, **destroy the scratch project**. Do not
leave customer rows sitting in an unused project.

---

## Vendor backup / PITR

Status: **CONFIRMED 2026-09-20** — read from the Supabase Management API with an
authenticated token (`GET /v1/projects/{ref}`, `/database/backups`,
`/v1/organizations/{slug}`). All three returned HTTP 200.

| Field | Value |
|---|---|
| Project ref | `fsldfzlxyavsuwqbceod` (name `MarketIntelligence`) |
| Organization | `ebhlfpiwuasxgkqcwsam` (`macro`) |
| Region / Postgres | `us-west-2` / 17.6.1.127 (engine 17, `ga`) |
| Plan | **`free`** |
| Daily backup retention | **none** — the API exposes no retention window on this plan |
| PITR enabled | **`false`** |
| PITR retention | n/a (disabled) |
| Available vendor backups | **`[]` — empty** |
| `walg_enabled` | `true` (internal WAL-G; exposes no restorable point on free) |
| Evidence | `GET /v1/projects/fsldfzlxyavsuwqbceod/database/backups` → `{"region":"us-west-2","walg_enabled":true,"pitr_enabled":false,"backups":[],"physical_backup_data":{}}` |

**Consequence.** On the free plan there is no vendor-side recovery point at all.
The encrypted R2 dump in this runbook is not a second line of defence — it is the
*only* line of defence. `auth.users` in particular has no recovery path, because it
is not in the dump and there is no PITR behind it. Raising the plan to Pro (daily
backups + optional PITR) is the only way to get a vendor-side restore point and the
only way to make `auth.users` recoverable.

---

## Scratch-Supabase restore receipt

Status: **PASS — GATE-1 closed 2026-09-20.** Real encrypted backup, real scratch
Supabase project, measured times, independently verified, scratch destroyed.

| Field | Value |
|---|---|
| Source backup identifier | `user-tables-20260920T112413Z` (mode `rest`, 27,888-byte `.tar.enc` + 1,941-byte manifest) |
| Backup taken at | 2026-09-20T11:24:13Z (`systemctl start macro-user-backup.service`, `Result=success`, exit 0) |
| Scratch project | `mmx-restore-scratch-20260920`, ref `hdxmdoodczwrvpobbbqp`, us-west-2, org `macro` |
| Restore command | `python -m scripts.backup_user_tables restore --backup-id user-tables-20260920T112413Z --dest-db-url "$SCRATCH_DB_URL" --i-am-restoring-into-scratch --write-receipt /tmp/mmx-restore-receipt.json` |
| Start (UTC) | 2026-09-20T11:29:01Z |
| End (UTC) | 2026-09-20T11:29:05Z |
| **Measured RTO** | **4 seconds** (target 30 min) |
| **Measured RPO** | **288 seconds** (declared 24 h) |
| Row / count / integrity | `integrity: pass`, `ok: true`; all nine tables `expected == restored` — profiles 39, watchlists 27, watchlist_symbols 288, chart_layouts 0, saved_scripts 4, alerts 1, favorites 0, user_entitlements 21, stripe_events 103 (483 rows) |
| Independent verification | Counts re-queried in scratch via Management API — all 9 match. Content-level `md5(string_agg(row::text))` compared production vs restored scratch for all 7 non-empty tables — **identical**. `pg_stat_user_tables` shows no table outside the 9-table allowlist received inserts. Production counts re-checked after the drill — unchanged. |
| Host | `ubuntu-s-mastermindx` (API VPS) — the only host holding R2 access + `BACKUP_ENCRYPTION_KEY`. The key was not copied to another machine. |
| Destination guard | Pooler DSN in **session mode (port 5432)**, not transaction mode (6543): `SET session_replication_role = replica` must persist across statements on one connection. |
| Scratch destruction | `DELETE /v1/projects/hdxmdoodczwrvpobbbqp` → HTTP 200. Verified: absent from `GET /v1/projects`; direct `GET` → **404 `Resource has been removed`**. Production `fsldfzlxyavsuwqbceod` still `ACTIVE_HEALTHY`. |
| Receipt `environment` | `scratch-postgres` (see caveat below) |

**Caveat on `gate1_scratch_supabase`.** The emitted receipt carries
`"gate1_scratch_supabase": false` even though this *was* a real scratch Supabase
project. That flag is derived from the transport (`environment == "scratch-supabase"`,
set only on the REST path), not from the destination's identity. The `--dest-db-url`
path this runbook prescribes always stamps `scratch-postgres`. The flag is wrong, not
the drill — the redacted `dest` in the receipt names the scratch project ref, and the
independent verification above is the real evidence. Fixed in the same change that
records this receipt.

---

## In-process fixture drill (machinery only — not GATE-1)

This is a local encrypt → publish → decrypt → restore → count-check against an
in-memory table store. It proves the script, the cipher, and the receipt
shape. It is **not** a scratch Supabase restore and does **not** close GATE-1.

Recorded by `tests/test_backup_user_tables.py::test_restore_roundtrip_memory_store_and_receipt`:

| Field | Value |
|---|---|
| Source backup identifier | `user-tables-20260815T051700Z` (fixture clock) |
| Restore commands | `python -m scripts.backup_user_tables restore --backup-id user-tables-20260815T051700Z --i-am-restoring-into-scratch --dest-db-url "$SCRATCH_DB_URL"` |
| Start / end | fixture clock 05:20:00Z → 05:20:08Z |
| Measured RTO | 8 seconds (in-process; not a network restore) |
| Measured RPO | 4800 seconds (fixture source `as_of` 04:00:00Z → restore start 05:20:00Z) |
| Integrity | pass — all nine tables, counts match the manifest |
| Environment | `in-process-fixture` (`gate1_scratch_supabase: false`) |

Re-run:

```bash
python -m pytest tests/test_backup_user_tables.py -q
```

---

## Failure notes

- Missing `BACKUP_ENCRYPTION_KEY`, dump source, or R2/`--local-dir` → exit 2,
  nothing uploaded.
- A missing protected table fails the dump (unless `--allow-missing` on a
  scratch drill). Partial archives are not published.
- `openssl` missing → refuse. Plaintext is never stored.
- Restoring over a scratch database that already has rows may duplicate.
  Prefer an empty scratch project.
- Losing the encryption key loses the R2 copies. The vendor backup (once
  confirmed) is then the only recovery path.
