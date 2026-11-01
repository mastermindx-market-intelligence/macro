# MedTech R14 release runbook

This is the release sequence for Macro PR #9816 and Terminal PR #1084. It records reviewed operations, not permission to bypass an unresolved gate. Original session names: **Upgrade MedTech Design References**, **Recover MedTech Session**.

Reviewed source baselines (actual release-head checks remain required):
- Macro backend semantics: `5f2233c41d7f9560eb26afa5597859c11b6c0ac7`.
- Terminal with repaired migration readback: `9d080bdca3bcce8ec10c1fce4e1ca30386d6d3c3`.
- Unapplied 0037 SQL: SHA-256 `c2e4831534fe2af7f835b19210020544b56b01866109a06b965ea656d87b8406`.

Record the actual canonical squash commits after acceptance. A reviewed branch head need not remain an ancestor after squash; compare the accepted scoped files to the reviewed hashes as well as recording canonical identity. Any later source change requires appropriate qualification. Do not call a published branch deployed.

## 1. Accept the compatible Macro backend

Before merging #9816, re-read its exact head, reviews, holds, mergeability, and all binding required checks. The dedicated MedTech job and source review do not replace ordinary CI.

Read back the accepted canonical commit and the two scoped migration decisions:
- `agentos/decisions/DEC-SUPABASE-MIGRATION-NAMESPACE-TERMINAL-LEDGER-2026-09-06.md` (reviewed SHA-256 `1ecb60bc20e0602c672953b2cd129137f6208e8043d618ee3f4fb5fd0db088bb`).
- `agentos/decisions/DEC-TERMINAL-MIGRATION-PR-LANDS-SOLO-WITH-LEDGER-FOLLOWUP.md` (reviewed SHA-256 `2bab76eeb953f2e16735a106690c3e4c9f2b82f6da82537bd4f4fa24202429f2`).

The scoped 0037 ordering disposition becomes effective only through ordinary canonical acceptance. It permits the bound migration on the qualified descendant; it does not waive Terminal's concluded required CI before production DDL.

## 2. Deploy Macro through its existing owner

Use the existing verified SSH identity and host `root@146.190.142.17`; credentials stay with their current owners. Never print their bytes.

```sh
/usr/local/bin/macro-update
```

This command runs on the VPS. It owns its existing lock, canonical fetch, deployment and API restart. Read back its actual result and deployed commit: a zero exit while another updater holds the lock is not deployment proof. First adoption can execute the predecessor updater inode while installing the new one; reconcile actual runtime state through this same owner before proceeding.

The updater/API prerequisite path creates only the fixed MedTech identity and empty private/public roots. It does not activate source acquisition. Do not clean unrelated live JSON, normalize the checkout manually, rerun initial infrastructure setup or replace deployment credentials.

## 3. Install refresh units dark, then attest the running API

Confirm current disk capacity. The worker requires at least 5 GiB free on each storage filesystem; an earlier read is not capacity at activation. No cleanup was needed in the October 20 preflight.

On the canonical VPS checkout:

```sh
bash /opt/macro/app/deploy/medtech-setup.sh
```

The installer validates prerequisites and unit files, refuses active/enabled refresh units and drop-in adoption, installs root-owned service/timer units and reloads daemon state. It starts and enables neither unit.

First installation only: review any existing environment file rather than overwriting it. Install the reviewed `app/deploy/medtech-environment.example` as `/etc/macro-medtech.env`, root:root, mode 0600. Only `MEDTECH_START_ON=YYYY-MM-DD` and comments are accepted; the date cannot be in the future. The reviewed example starts on 2026-01-01.

Ensure the reviewed `macro-api.service` fragment has been installed, daemon state reloaded and the API restarted through the existing owner. Then:

```sh
/usr/bin/python3 -I /opt/macro/app/deploy/medtech-api-boundary.py
```

The boundary script is an attestation, not an installer. It requires the environment file, exact installed API fragment, no drop-ins, no pending daemon reload, a stable running process, and actual read-only public / inaccessible private mounts. The worker repeats this attestation in `ExecStartPre`. Do not bypass a refusal.

Reviewed boundary SHA-256: `aa8c9d51af0c219ff64576a97dc7a3a6bea010599d7a2fdcd7dea5f1c90257ee`.

## 4. Run the first complete refresh before starting the timer

```sh
systemctl start macro-medtech.service
systemctl show macro-medtech.service -p Result,ExecMainStatus,ExecMainExitTimestamp
```

The worker runs as the dedicated nonroot account, bounded to 15 minutes, 512 MiB and 10,000 records per endpoint. It acquires the explicitly configured interval, not all FDA history. No automatic retry is configured.

Inspect the exit, publication generation and source clocks, and the health response through the authorized consumer. Distinguish public-projection verification from authenticated API verification. Existing baseline records are reference history, not newly announced decisions. Failed refresh retains the preceding valid publication and reports failure.

Only after the first complete refresh is accepted:

```sh
systemctl enable --now macro-medtech.timer
systemctl is-enabled macro-medtech.timer
systemctl is-active macro-medtech.timer
systemctl list-timers macro-medtech.timer
```

The timer is daily at 06:10 UTC with up to 20 minutes of jitter. Its persistent schedule can trigger a catch-up invocation on activation. Record actual scheduling and resulting worker state; enablement alone does not prove a successful run.

## 5. Qualify the actual Terminal head before production 0037

This gate may proceed in parallel with Macro deployment, but DDL requires the accepted canonical policy and concluded required checks on the actual Terminal release head.

1. Reconcile any material changes from current master before accepting the release head and its CI. Do not integrate a new master after qualification and assume the old checks still describe the result. Ancestry-only movement need not force an unnecessary refresh.
2. Re-read the open PR namespace and active train state. Confirm #1084 is the unique 0037 owner, preserve every inherited canonical row, and retain 0035's hold.
3. Preserve 0036's existing application evidence from #1044. It was applied on 2026-10-19; never replay it.
4. Confirm a clean source checkout and the exact bound SQL hash. Run the repository's namespace checker and its PR-mode tests.
5. Perform a fresh read-only production catalog preflight for the bound 0037 objects and dependencies. The earlier read found no MedTech tables/functions/constraints; recheck immediately before application.
6. Run the reviewed per-file applier's dry run. It must recognize one atomic DO statement, twelve expected typed objects and both readback queries without excluded SQL. Dry-run parsing does not establish actual catalog closure; the local 38-check applier qualification and production post-readback are separate evidence.

The complete October 20 namespace census covered 158 open PRs and 4,463 changed-file entries. It is evidence of that census time, not a permanent namespace lease. The carrier also reconciles inherited 0036 ownership truth; do not assert that its entire ledger diff against master contains only 0037.

The project reference is `fsldfzlxyavsuwqbceod`. The primary credential owner remains `/Users/chriswong/Documents/Cluade/charting-app/.env`; use the reviewed parser without logging secrets and cross-check the resolved project. An explicit project-ref mismatch is a hard stop.

## 6. Apply only the bound 0037 file, then post its receipt

From the accepted clean Terminal checkout, use the reviewed parser to supply the token and project reference from the existing primary credential owner to the applier's child-process environment, without printing their values or copying them into the worktree. Override unintended ambient values; do not rely on an unrelated worktree .env. Confirm that dry-run resolved and checked the expected project; an unresolved-credentials note does not satisfy this prerequisite.

Select a fresh, absent receipt filename and confirm that its parent exists and is writable before application. Preserve the invocation's evidence. Never reuse a previous attempt's receipt path.

```sh
python3 scripts/supabase_apply.py supabase/migrations/0037_medtech_watches.sql --dry-run --project-ref fsldfzlxyavsuwqbceod
python3 scripts/supabase_apply.py supabase/migrations/0037_medtech_watches.sql --apply --receipt <receipt-path>.json --project-ref fsldfzlxyavsuwqbceod
```

The tool sends one named file statement at a time. This particular file encloses its DDL in one DO statement; do not generalize that atomicity to multi-statement migrations. The token travels through curl's stdin configuration, never its arguments.

Inspect the exact pre-apply and post-apply catalog receipt. Require the twelve expected objects with their correct kinds, public schema, owning tables and function signatures, plus forced RLS, expected policy/guard counts and the intended privilege matrix. The incumbent matcher compares bare names: its `applied` status alone cannot distinguish a trigger from its same-named function. The new local qualification includes that negative control and preserves the original 7,106-byte executable DO span (SHA-256 `a6845559c01e3e22f141992d1be9f80b6892dbdf582539fb35d456d821273985`). Post the receipt on #1084 and read it back **before** updating the 0037 applied flags and README application row. Retain the original applied SQL SHA and source head. Keep its PR state open until actual merge. Do not apply the entire migration directory or use a different runner.

A 401 requires human rotation of the existing primary Management PAT; no alternate credential or carrier replay. For any unknown or failed effect, read the existing receipt and catalog to reconcile that same attempt before considering another write. A missing receipt after interruption or a receipt-write failure does not establish that no DDL occurred; reconcile that same attempt using its available output and current catalog.

## 7. Solo Terminal landing and immediate ledger follow-up

After the receipt has been posted/read back, update only the truthful 0037 application metadata and its README summary. Run affected qualification and all ordinary exact-head gates required for the resulting candidate. Keep #1084 outside an active landing train.

Squash #1084 only when accepted and green, with an expected-head fence. Immediately create the minimal follow-up recording its actual squash SHA and merged PR state in the ledger, SQL header and README. Retain the original applied-source hash in the receipt; a subsequent header-only change is not a second application. The follow-up must land before subsequent landing-train activity.

Record both the initial MedTech squash and the post-follow-up canonical master target. Do not infer either from the old branch head.

## 8. Deploy the exact canonical Terminal target

The authoritative deployed owner is Terminal's `ops/terminal-build.sh`, installed at `/opt/terminal/terminal-build.sh`. Macro's older Terminal build script is not interchangeable.

Reviewed owner SHA-256: `c6759cc653e0f19102a015ec52842795bde24eb85766d2e73f3024b4eefe409d`.

Read back the installed owner's identity and verify that it implements the accepted reviewed owner contract before invoking it. If the installed file is a predecessor, use the documented first-adoption entrance from one exact protected ops bundle containing the owner, preflight script, reviewed policy and audit package. This remains the existing owner lifecycle; do not replace the installed script manually or assume that supplying --target-sha upgrades an older owner.

```sh
bash /opt/terminal/terminal-build.sh --target-sha <full-post-follow-up-canonical-SHA>
```

The owner requires a full 40-hex target, runs its source preflight, proves that exact target inside freshly observed canonical master, and owns build/swap/health/readback. No branch-tip inference or old rsync path.

The preflight intentionally writes an immutable receipt outside source roots. It gates source reset, build and activation; it does not promise zero host writes. Its policy digest is over canonical parsed JSON, not raw file bytes. The owner has a narrow receipted recovery for sole CANONICAL_HEAD_MISMATCH; operators must not generalize it to other refusals.

Automatic recovery covers guarded .next/deployment-marker swap and associated restart/health/identity failures, plus guarded pre-swap canonical recovery. Missing backups or failed recovery remain unresolved. App generation is committed before later runtime-overlay/source-sync work, so a later failure requires reconciliation and live readback. This is not whole-release, dependency or database rollback.

## 9. Verify the genuine signed-in watch workflow

The existing browser account was confirmed Pro on October 20. Reuse that browser and the owned MedTech verification tab at `/discover?tab=medtech`; use an authentication handoff only if the session now requires it.

1. Find a supported parent P-number PMA family and open its record/source. Legacy N identifiers remain eligible for exact-event watches, not family watches.
2. Save the family watch with both supported triggers, reload, and reopen the same watch URL. Record the UUID visible in the UI.
3. Take a reviewed read-only database projection scoped to that exact UUID: `id, subject_type, subject_id, triggers, baseline_generation, baseline_revision, baseline_at, version`.
4. In the UI, remove the new-supplement trigger, save, reload and reopen. Read the same scoped projection again. Identity and all baseline fields must remain byte-exact, with version incremented by one. Preserve raw timestamp strings; the minute-resolution UI is not the baseline evidence. Restore the original triggers if appropriate, recording the further version increment.
5. Inspect changes. Exercise MarkReviewed only if an actual eligible post-baseline revision is available. Otherwise record the empty state and mark successful live review as unexercised.

Do not manufacture a source revision, backdate a watch or force an acknowledgment to satisfy this check. An unchanged source recapture is a sighting, not a new revision. New-supplement eligibility also requires the source decision date strictly after the watch's baseline calendar day.

One successful watch does not prove concurrent quota enforcement, account isolation, failure paths or all historical workflows. Keep the isolated SQL, 39 browser fixtures, current production observation and any unexercised case distinct.

## Recovery boundaries

- Stop source scheduling with `systemctl disable --now macro-medtech.timer` when required; retain private evidence and published generations. API/source rollback follows existing Git/deployment owners.
- Never run the destructive 0037 down block in production. Disable watch routes through an ordinary reviewed Terminal revision if needed, retaining account data.
- A generation conflict in the browser and an app-generation deployment failure are different cases. The UI retains its last displayed state on failed refresh; this does not prove deployment rollback.
- Uncertain effects permit read-only reconciliation through the current owners, not duplicate writes through another tool, account or carrier.

## Short checkpoint

Record: accepted/published/deployed identities; checks actually concluded; boundary result; first-refresh generation/source clocks; timer enabled and active state; 0037 pre/post receipt and posted URL; solo squash and follow-up SHAs; exact Terminal deployment receipt; genuine watch UUID and baseline/version comparison; successful live review exercised or unexercised; next three steps and the exact input needed for any blocker.

Sources: the immutable deployment files, SQL and scoped decisions linked above; `docs/medtech_backend.md`, Terminal `scripts/README_supabase_apply.md`, `ops/TERMINAL_RELEASE_PREFLIGHT.md` and `docs/medtech_watches.md`. The deployment sequencing and recovery scope were independently reviewed against the two pinned heads; this runbook incorporates the resulting corrections.
